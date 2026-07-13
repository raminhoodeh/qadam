"""Public-safe Pattern Discovery and Quantum Review dashboard projections.

These projections explain canonical research evidence. They do not promote
patterns, create strategy hypotheses, approve risk, create orders, write to a
broker, or grant proof credit.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    unique_errors,
    validate_authority,
)
from orchestrator.qadam_wave_b_common import parse_timestamp, safe_float, safe_int, stable_id

SCHEMA_VERSION = "qadam_pattern_dashboard_views.v1"
PATTERN_DISCOVERY_ARTIFACT = "qadam_pattern_discovery_dashboard.json"
QUANTUM_REVIEW_ARTIFACT = "qadam_quantum_review_dashboard.json"

PATTERN_SCORE_ARTIFACT = "qadam_pattern_score_v3_records.jsonl"
PATTERN_SCORE_TAPE_PROGRESS_ARTIFACT = "qadam_pattern_score_tape_progress.json"
FORWARD_LABEL_MANIFEST_ARTIFACT = "qadam_forward_label_manifest.json"
STATISTICAL_BACKTEST_CHECKS_ARTIFACT = "qadam_statistical_backtest_checks.json"
EDGE_REGISTRY_ARTIFACT = "qadam_edge_registry.jsonl"
EDGE_SUMMARY_ARTIFACT = "qadam_edge_registry_summary.json"
BACKFILL_SUMMARY_ARTIFACT = "qadam_backfill_dashboard_summary.json"
NONLINEAR_EXPERIMENT_ARTIFACT = "qadam_nonlinear_experiment_registry.jsonl"
QUANTUM_COMPARISON_ARTIFACT = "qadam_quantum_classical_comparison.jsonl"
QUANTUM_USEFULNESS_ARTIFACT = "qadam_quantum_usefulness_summary.json"
NONLINEAR_OVERFIT_ARTIFACT = "qadam_nonlinear_overfit_audit.json"

PUBLIC_AUTHORITY = {
    "read_only": True,
    "public_safe": True,
    "command_disabled": True,
    "paper_only": True,
    "trade_candidate_creation_allowed": False,
    "risk_approval_allowed": False,
    "execution_approval_allowed": False,
    "paper_order_allowed": False,
    "broker_write_allowed": False,
    "proof_credit_allowed": False,
    "telegram_command_path_enabled": False,
    "live_capital_enabled": False,
}

STRATEGY_COPY: dict[str, dict[str, Any]] = {
    "crude_oil_energy_security_disruption": {
        "title": "Physical disruption pressure across crude-oil proxies",
        "market": "Crude oil and energy",
        "relationship_type": "cross-source event-to-price lead/lag",
        "question": (
            "Do conflict and physical supply disruptions appear before crude-oil and "
            "energy prices fully reprice the risk?"
        ),
        "analysis": (
            "Qadam is combining conflict, maritime, fire and conflict-tracker evidence "
            "to test a possible energy-supply repricing relationship."
        ),
        "why_quantum": (
            "The effect may depend on several disruptions arriving together, their order, "
            "and the prevailing volatility regime."
        ),
        "interaction": (
            "Test whether joint conflict, maritime and physical-disruption states explain "
            "future crude returns better than the matched linear baseline."
        ),
        "falsifiers": [
            "Disruption clusters do not precede cost-adjusted crude or energy returns.",
            "The relationship disappears on untouched holdout periods.",
            "A simpler classical baseline performs equally well after penalties.",
        ],
    },
    "defence_repricing_geopolitical_watch": {
        "title": "Geopolitical repricing pressure across defence assets",
        "market": "Defence and aerospace",
        "relationship_type": "cross-source policy and event repricing",
        "question": (
            "Do conflict, filings, public-policy and innovation signals appear before "
            "defence assets reprice?"
        ),
        "analysis": (
            "Qadam is comparing conflict evidence with filings, patents and public trading "
            "disclosures to test whether defence repricing is delayed."
        ),
        "why_quantum": (
            "The relationship may depend on combinations of conflict intensity, policy "
            "attention and company-specific evidence rather than one dominant signal."
        ),
        "interaction": (
            "Test whether nonlinear combinations of geopolitical and company evidence add "
            "holdout value beyond a linear defence-factor baseline."
        ),
        "falsifiers": [
            "Defence returns do not follow the source configuration consistently.",
            "The effect is explained by the broad equity market.",
            "Nonlinear interactions do not improve untouched holdout performance.",
        ],
    },
    "prediction_market_geopolitical_dislocation": {
        "title": "Event-market odds diverging from geopolitical evidence",
        "market": "Prediction markets",
        "relationship_type": "source-to-probability divergence",
        "question": (
            "Do event-market probabilities diverge from the wider geopolitical evidence "
            "before the gap closes?"
        ),
        "analysis": (
            "Qadam is comparing prediction-market odds with conflict, news and narrative "
            "evidence to test whether event probabilities are temporarily misaligned."
        ),
        "why_quantum": (
            "Probability gaps may depend on interacting event, narrative and liquidity "
            "states that are not captured by one linear relationship."
        ),
        "interaction": (
            "Test whether joint event, narrative and market-liquidity states improve the "
            "prediction of probability convergence."
        ),
        "falsifiers": [
            "Observed probability gaps do not close more reliably than chance.",
            "The result is driven by thin or unavailable market data.",
            "The nonlinear comparison fails on event-level holdouts.",
        ],
    },
    "semiconductor_policy_options_asymmetry": {
        "title": "Policy and innovation pressure across semiconductor assets",
        "market": "Semiconductors and technology",
        "relationship_type": "policy and innovation repricing",
        "question": (
            "Do policy, filing, patent and news signals appear before semiconductor assets "
            "fully reflect the change?"
        ),
        "analysis": (
            "Qadam is combining policy/news, filing, patent and disclosure evidence to test "
            "a possible delayed semiconductor repricing relationship."
        ),
        "why_quantum": (
            "The direction may change with the policy regime, supply-chain state and the "
            "particular combination of companies affected."
        ),
        "interaction": (
            "Test whether regime-conditioned policy and innovation interactions add "
            "holdout value beyond the classical technology baseline."
        ),
        "falsifiers": [
            "The source combination does not precede semiconductor-relative returns.",
            "The effect is explained by broad technology momentum.",
            "The interaction model is unstable across policy regimes.",
        ],
    },
    "silver_macro_liquidity_stress": {
        "title": "Macro liquidity pressure across silver proxies",
        "market": "Silver and precious metals",
        "relationship_type": "macro-regime lead/lag",
        "question": (
            "Do rates, liquidity, trade and commodity signals appear before silver changes "
            "its behavior relative to gold and risk assets?"
        ),
        "analysis": (
            "Qadam is combining central-bank, macro, trade and commodity evidence to test "
            "whether silver is entering a repeatable liquidity-stress regime."
        ),
        "why_quantum": (
            "Silver can behave as an industrial metal, precious metal or stress asset, so "
            "the useful relationship may be regime-dependent and nonlinear."
        ),
        "interaction": (
            "Test whether macro-state transitions and entropy features improve silver "
            "outcomes beyond the matched linear macro baseline."
        ),
        "falsifiers": [
            "Silver outcomes do not differ after the recorded macro configuration.",
            "The relationship is confined to one historical period.",
            "The nonlinear method adds no net untouched-holdout value.",
        ],
    },
}

MISSING_FEATURE_COPY = {
    "current_market_price": "current market price",
    "fresh_source_quorum": "enough fresh independent sources",
    "paperability_context": "paper-market availability",
    "volatility_context": "current volatility context",
    "volume_or_flow_context": "current volume or market-flow context",
}

METHOD_COPY = {
    "nonlinear_feature_interactions": "Nonlinear feature interactions",
    "regime_path_dependence": "Regime and path dependence",
    "ordinal_permutation_entropy": "Ordinal and permutation entropy",
    "clustering_state_transitions": "Market-state transitions",
    "constrained_combinatorial_feature_selection": "Constrained feature combinations",
    "quantum_kernel_or_circuit_inspired": "Quantum-inspired kernel or circuit method",
}


def _records_generated_at(records: list[dict[str, Any]]) -> str | None:
    timestamps = [
        str(record.get("scoring_as_of") or record.get("generated_at"))
        for record in records
        if record.get("scoring_as_of") or record.get("generated_at")
    ]
    return max(timestamps) if timestamps else None


def _age_seconds(value: Any, reference: str) -> int | None:
    observed = parse_timestamp(value)
    current = parse_timestamp(reference)
    if observed is None or current is None:
        return None
    return max(0, int((current - observed).total_seconds()))


def _freshness(value: Any, reference: str, threshold_seconds: int = 30 * 60) -> dict[str, Any]:
    age = _age_seconds(value, reference)
    if not value:
        state = "missing"
    elif age is None or age > threshold_seconds:
        state = "stale"
    else:
        state = "fresh"
    return {
        "observed_at": value,
        "age_seconds": age,
        "stale_after_seconds": threshold_seconds,
        "state": state,
        "is_current": state == "fresh",
    }


def _count(payload: dict[str, Any], *keys: str) -> int:
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return safe_int(value)
    for container_key in ("counts", "summary", "progress", "metrics"):
        container = payload.get(container_key)
        if not isinstance(container, dict):
            continue
        for key in keys:
            value = container.get(key)
            if value is not None:
                return safe_int(value)
    return 0


def _score_groups(scores: list[dict[str, Any]]) -> list[tuple[tuple[str, ...], list[dict[str, Any]]]]:
    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for score in scores:
        family = str(score.get("strategy_family_id") or "").strip()
        if not family or family not in STRATEGY_COPY or score.get("negative_control") is True:
            continue
        source_keys = sorted(
            {
                str(row.get("source_key"))
                for row in score.get("feature_inputs") or []
                if isinstance(row, dict) and row.get("source_key")
            }
        )
        key = (
            family,
            str(score.get("direction_hypothesis") or "undetermined"),
            str(score.get("horizon_hypothesis") or "unmeasured"),
            "|".join(source_keys),
        )
        grouped[key].append(score)
    return list(grouped.items())


def _edge_for_group(
    edges: list[dict[str, Any]], family: str, instruments: list[str]
) -> dict[str, Any]:
    instrument_set = set(instruments)
    for edge in edges:
        if edge.get("strategy_family_id") == family:
            return edge
        if edge.get("instrument") in instrument_set:
            return edge
    return {}


def _empirical_comparison(record: dict[str, Any]) -> bool:
    return (
        record.get("classical_holdout_metric") is not None
        and record.get("nonlinear_or_quantum_holdout_metric") is not None
    )


def _route(module_id: str, view_id: str, label: str, reason: str) -> dict[str, str]:
    return {
        "module_id": module_id,
        "view_id": view_id,
        "label": label,
        "reason": reason,
    }


def _relationship_stage(
    edge: dict[str, Any], score_tape_rows: int, forward_labels: int, backtest_runs: int
) -> tuple[str, str, str]:
    edge_state = str(
        edge.get("edge_state")
        or edge.get("promotion_class")
        or edge.get("confidence_class")
        or ""
    ).lower()
    if edge and any(token in edge_state for token in ("validated", "promoted", "supported")):
        return "validated_edge", "Validated edge", "validated_edges"
    if backtest_runs > 0 or forward_labels > 0:
        return "under_historical_test", "Under historical test", "under_testing"
    if score_tape_rows > 0:
        return "awaiting_forward_labels", "Awaiting forward outcomes", "under_testing"
    return "awaiting_historical_evidence", "Awaiting historical evidence", "under_testing"


def _missing_feature_labels(records: list[dict[str, Any]]) -> list[str]:
    values = {
        str(item)
        for record in records
        for item in (record.get("missing_critical_features") or [])
        if item
    }
    return [MISSING_FEATURE_COPY.get(value, value.replace("_", " ")) for value in sorted(values)]


def _relationship_record(
    key: tuple[str, ...],
    records: list[dict[str, Any]],
    *,
    generated_at: str,
    edges: list[dict[str, Any]],
    score_tape_rows: int,
    forward_labels: int,
    backtest_runs: int,
    comparisons: list[dict[str, Any]],
) -> dict[str, Any]:
    family, direction, horizon, source_signature = key
    copy = STRATEGY_COPY[family]
    instruments = sorted({str(record.get("instrument")) for record in records if record.get("instrument")})
    source_keys = source_signature.split("|") if source_signature else []
    edge = _edge_for_group(edges, family, instruments)
    stage, stage_label, tab = _relationship_stage(
        edge, score_tape_rows, forward_labels, backtest_runs
    )
    observed_at = _records_generated_at(records)
    freshness = _freshness(observed_at, generated_at)
    instrument_results = sorted(
        [
            {
                "instrument": str(record.get("instrument") or "unknown"),
                "raw_pattern_score": round(safe_float(record.get("raw_pattern_score")), 6),
                "raw_pattern_score_is_probability": False,
                "confidence_state": record.get("confidence_state"),
                "missing_context": [
                    MISSING_FEATURE_COPY.get(str(value), str(value).replace("_", " "))
                    for value in record.get("missing_critical_features") or []
                ],
            }
            for record in records
        ],
        key=lambda row: (-safe_float(row["raw_pattern_score"]), row["instrument"]),
    )
    best_score = max((safe_float(row.get("raw_pattern_score")) for row in records), default=0.0)
    feature_inputs = [
        row
        for record in records
        for row in (record.get("feature_inputs") or [])
        if isinstance(row, dict)
    ]
    unique_inputs = {
        str(row.get("source_key")): row for row in feature_inputs if row.get("source_key")
    }
    fresh_source_count = sum(row.get("fresh") is True for row in unique_inputs.values())
    missing_context = _missing_feature_labels(records)
    family_comparisons = [
        row for row in comparisons if row.get("strategy_family_id") == family
    ]
    empirical_quantum = [row for row in family_comparisons if _empirical_comparison(row)]
    if stage == "validated_edge":
        destination = _route(
            "decide",
            "strategies",
            "Core Strategies",
            "Map the validated relationship into a bounded strategy hypothesis.",
        )
        advance_when = [
            "The edge registry remains validated under the frozen evidence policy.",
            "The strategy mapping records entry logic, invalidation and paperability limits.",
        ]
    elif empirical_quantum:
        destination = _route(
            "patterns",
            "nonlinear",
            "Quantum Review",
            "Read the completed classical-versus-quantum comparison.",
        )
        advance_when = [
            "The integrated classical and quantum evidence passes the frozen validation policy."
        ]
    else:
        destination = _route(
            "learn",
            "replay",
            "Backtesting & Replay",
            "Collect provider-backed outcomes and run the frozen historical test.",
        )
        advance_when = [
            "Provider-backed historical feature rows exist.",
            "Forward outcomes mature after the score timestamp.",
            "Leakage checks pass and an untouched holdout remains available.",
        ]
    blockers = []
    if score_tape_rows == 0:
        blockers.append("No provider-backed historical score-tape rows exist yet.")
    if forward_labels == 0:
        blockers.append("No forward outcome labels have matured yet.")
    blockers.extend(f"Missing {value}." for value in missing_context)
    if freshness["state"] != "fresh":
        blockers.append("The latest observation is out of date and is not a current live signal.")
    pattern_id = stable_id("pattern-relationship", *key)
    direction_label = direction.replace("_", " ")
    horizon_label = horizon.replace("_forward", " sessions").replace("_", " ")
    source_preview = ", ".join(source_keys[:4])
    if len(source_keys) > 4:
        source_preview += f", plus {len(source_keys) - 4} more"
    return {
        "pattern_id": pattern_id,
        "strategy_family_id": family,
        "title": copy["title"],
        "plain_english_question": copy["question"],
        "plain_english_analysis": (
            f"{copy['analysis']} At the latest scoring cut, {fresh_source_count} of "
            f"{len(unique_inputs)} contributing sources were fresh. This is a research "
            "observation, not evidence that the market outcome will occur."
        ),
        "stage": stage,
        "stage_label": stage_label,
        "tab": tab,
        "relationship_type": copy["relationship_type"],
        "source_signal": (
            f"{source_preview} contributed to the latest point-in-time research score."
            if source_preview
            else "No source contribution was exported."
        ),
        "source_chain": source_keys,
        "fresh_source_count": fresh_source_count,
        "contributing_source_count": len(unique_inputs),
        "fresh_source_ratio": round(
            fresh_source_count / len(unique_inputs), 6
        ) if unique_inputs else 0.0,
        "target_market": copy["market"],
        "target_instruments": instruments,
        "direction": direction_label,
        "direction_is_hypothesis": True,
        "horizon": horizon_label,
        "horizon_is_validated": False,
        "regime": "not established",
        "raw_pattern_score": round(best_score, 6),
        "raw_pattern_score_is_probability": False,
        "raw_pattern_score_label": f"Research score {best_score:.3f}",
        "calibration_state": "not calibrated",
        "historical_evidence": {
            "provider_backed_score_rows": score_tape_rows,
            "forward_label_count": forward_labels,
            "backtest_run_count": backtest_runs,
            "validated_edge": stage == "validated_edge",
            "net_expectancy_after_costs": edge.get("net_expectancy"),
            "independent_occurrence_count": edge.get("independent_occurrence_count"),
            "holdout_state": edge.get("holdout_state") or "not available",
            "summary": (
                "A validated cost-adjusted edge is registered."
                if stage == "validated_edge"
                else "Historical outcomes have not yet established a repeatable edge."
            ),
        },
        "current_live_match": {
            "state": "recorded_observation" if freshness["is_current"] else "stale_observation",
            "is_active": freshness["is_current"] and stage == "validated_edge",
            "summary": (
                "The evidence is current, but it is not a live trade signal."
                if freshness["is_current"]
                else "The latest score is out of date and cannot describe current market conditions."
            ),
        },
        "classical_result": {
            "state": "not_measured" if backtest_runs == 0 else "available",
            "summary": (
                "No empirical classical backtest has completed."
                if backtest_runs == 0
                else "Classical backtest evidence is available in Backtesting & Replay."
            ),
        },
        "quantum_review": {
            "state": "not_measurable" if not empirical_quantum else "comparison_available",
            "empirical_comparison_count": len(empirical_quantum),
            "summary": (
                "Quantum usefulness is not measurable without an untouched holdout."
                if not empirical_quantum
                else "An empirical classical-versus-quantum comparison is available."
            ),
            "route": _route(
                "patterns", "nonlinear", "Quantum Review", "Inspect nonlinear comparison evidence."
            ),
        },
        "integrated_verdict": {
            "state": "validated" if stage == "validated_edge" else "unproven",
            "summary": (
                "The frozen validation policy supports this relationship."
                if stage == "validated_edge"
                else "The current score records an idea to test; it does not prove an edge."
            ),
        },
        "mapped_strategy": {
            "strategy_family_id": family,
            "label": str(records[0].get("strategy_label") or family.replace("_", " ").title()),
        },
        "current_stage": stage_label,
        "next_destination": destination,
        "advance_when": advance_when,
        "failure_destination": "Disproved or faded relationships",
        "blocked_by": blockers or ["No research blocker is recorded."],
        "falsifiers": copy["falsifiers"],
        "freshness": freshness,
        "observed_at": observed_at,
        "instrument_results": instrument_results,
        "stage_key": stage,
        "market_affected": copy["market"],
        "instrument_symbols": instruments,
        "strategy_fit": str(
            records[0].get("strategy_label") or family.replace("_", " ").title()
        ),
        "evidence_quality_score": round(best_score, 6),
        "detected_signal": copy["question"],
        "source_signal_summary": (
            f"{fresh_source_count} of {len(unique_inputs)} contributing sources were fresh "
            "at the scoring cut."
        ),
        "price_relationship": (
            "A validated cost-adjusted relationship is registered."
            if stage == "validated_edge"
            else "No historical source-price relationship has been validated yet."
        ),
        "what_qadam_thinks": copy["analysis"],
        "what_would_confirm": " ".join(advance_when),
        "what_blocks_trade": " ".join(blockers) if blockers else "No research blocker is recorded.",
        "next_action": destination["reason"],
        "rank_badges": [],
        "artifact_refs": [
            f"data/runtime/{PATTERN_SCORE_ARTIFACT}",
            f"data/runtime/{PATTERN_SCORE_TAPE_PROGRESS_ARTIFACT}",
            f"data/runtime/{FORWARD_LABEL_MANIFEST_ARTIFACT}",
            f"data/runtime/{EDGE_REGISTRY_ARTIFACT}",
        ],
        **PUBLIC_AUTHORITY,
        "authority": authority_flags(),
    }


def build_pattern_discovery_projection(
    *,
    generated_at: str,
    scores: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    score_tape: dict[str, Any],
    forward_labels: dict[str, Any],
    backtest: dict[str, Any],
    edge_summary: dict[str, Any],
    backfill: dict[str, Any],
    comparisons: list[dict[str, Any]],
) -> dict[str, Any]:
    score_tape_rows = _count(score_tape, "score_tape_row_count", "record_count")
    eligible_snapshots = _count(
        score_tape,
        "eligible_historical_decision_point_count",
        "eligible_score_input_count",
    )
    label_count = _count(forward_labels, "label_count", "forward_label_count")
    backtest_runs = _count(backtest, "backtest_run_count", "fold_count", "paired_record_count")
    validated_count = _count(edge_summary, "validated_edge_count")
    relationships = [
        _relationship_record(
            key,
            records,
            generated_at=generated_at,
            edges=edges,
            score_tape_rows=score_tape_rows,
            forward_labels=label_count,
            backtest_runs=backtest_runs,
            comparisons=comparisons,
        )
        for key, records in _score_groups(scores)
    ]
    stage_rank = {
        "validated_edge": 0,
        "under_historical_test": 1,
        "awaiting_forward_labels": 2,
        "awaiting_historical_evidence": 3,
    }
    relationships.sort(
        key=lambda row: (
            stage_rank.get(str(row.get("stage")), 9),
            -(parse_timestamp(row.get("observed_at")) or datetime.min.replace(tzinfo=timezone.utc)).timestamp(),
            -safe_float(row.get("raw_pattern_score")),
            str(row.get("title")),
        )
    )
    fresh_relationships = [
        row for row in relationships if row.get("freshness", {}).get("is_current") is True
    ]
    valid_relationships = [row for row in relationships if row.get("stage") == "validated_edge"]
    highest = max(relationships, key=lambda row: safe_float(row.get("raw_pattern_score")), default=None)
    qualitative_bullets = []
    for row in relationships[:5]:
        instruments = ", ".join(row.get("target_instruments", [])[:4])
        if len(row.get("target_instruments", [])) > 4:
            instruments += f", plus {len(row['target_instruments']) - 4} more"
        qualitative_bullets.append(
            {
                "pattern_id": row["pattern_id"],
                "title": row["title"],
                "body": (
                    f"{row['plain_english_analysis']} Affected instruments: {instruments or 'not exported'}. "
                    f"Next: {row['next_destination']['label']}."
                ),
                "stage": row["stage_label"],
                "observed_at": row.get("observed_at"),
                "raw_pattern_score": row["raw_pattern_score"],
                "raw_pattern_score_label": row["raw_pattern_score_label"],
                "fresh_source_count": row["fresh_source_count"],
                "contributing_source_count": row["contributing_source_count"],
                "fresh_source_ratio": row["fresh_source_ratio"],
            }
        )
    strategy_linked_score_record_count = sum(
        len(row.get("instrument_results") or []) for row in relationships
    )
    context_and_control_score_record_count = max(
        0, len(scores) - strategy_linked_score_record_count
    )
    source_count = _count(backfill, "source_count")
    instrument_count = _count(backfill, "instrument_count")
    mapped_relationships = _count(backfill, "relationship_count")
    if mapped_relationships == 0 and source_count and instrument_count:
        mapped_relationships = source_count * instrument_count
    tab_counts = {
        "live_observations": len(fresh_relationships),
        "under_testing": sum(row.get("tab") == "under_testing" for row in relationships),
        "validated_edges": len(valid_relationships),
        "rejected_or_decayed": sum(
            row.get("tab") == "rejected_or_decayed" for row in relationships
        ),
    }
    default_tab = (
        "validated_edges"
        if tab_counts["validated_edges"]
        else "under_testing"
        if tab_counts["under_testing"]
        else "live_observations"
    )
    latest_observation = max(
        (row.get("observed_at") for row in relationships if row.get("observed_at")),
        default=None,
    )
    status = "validated_edges_visible" if valid_relationships else "awaiting_empirical_evidence"
    headline = (
        f"{len(valid_relationships)} repeatable historical edge"
        f"{'s have' if len(valid_relationships) != 1 else ' has'} passed validation."
        if valid_relationships
        else "No repeatable historical edge has been validated yet."
    )
    analysis_summary = (
        f"The latest scoring pass produced {len(relationships)} distinct research "
        "observations. "
    )
    if highest:
        analysis_summary += (
            f"{highest['title']} has the highest raw research score, but that score is "
            "not yet calibrated against historical outcomes. "
        )
    analysis_summary += (
        "The bullets below describe what Qadam most recently recorded, not trades or "
        "validated predictions."
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_pattern_discovery_dashboard",
        "generated_at": generated_at,
        "status": status,
        "headline": headline,
        "plain_english_summary": (
            f"Qadam has {len(relationships)} distinct source-to-market relationships under "
            f"review, {eligible_snapshots} eligible historical snapshots, {backtest_runs} "
            f"completed backtest runs and {validated_count} validated edges."
        ),
        "purpose": (
            "Qadam compares world events, source activity and market prices to test whether "
            "specific signals repeatedly appeared before specific market outcomes."
        ),
        "qualitative_analysis": {
            "title": "What Qadam most recently noticed",
            "summary": analysis_summary,
            "bullet_count": len(qualitative_bullets),
            "bullets": qualitative_bullets,
            "total_score_record_count": len(scores),
            "strategy_linked_score_record_count": strategy_linked_score_record_count,
            "context_and_control_score_record_count": context_and_control_score_record_count,
            "score_record_explanation": (
                f"The {len(qualitative_bullets)} observations are one plain-English summary "
                f"per distinct relationship. They roll up {strategy_linked_score_record_count} "
                f"strategy-linked instrument readings. The remaining "
                f"{context_and_control_score_record_count} score records are market-wide "
                "context or control checks, not additional discoveries."
            ),
            "boundary": "Recent observations are research records, not validated edges or trade signals.",
        },
        "freshness": _freshness(latest_observation, generated_at),
        "universe": {
            "source_count": source_count,
            "instrument_count": instrument_count,
            "mapped_relationship_count": mapped_relationships,
        },
        "funnel": [
            {"key": "mapped", "label": "Relationships mapped", "count": mapped_relationships},
            {"key": "recorded", "label": "Instrument score records", "count": len(scores)},
            {"key": "eligible", "label": "Eligible historical snapshots", "count": eligible_snapshots},
            {"key": "backtested", "label": "Backtested relationships", "count": backtest_runs},
            {"key": "validated", "label": "Validated edges", "count": validated_count},
            {"key": "active", "label": "Active live matches", "count": sum(row["current_live_match"]["is_active"] for row in relationships)},
        ],
        "tabs": [
            {"key": "live_observations", "label": "Live observations", "count": tab_counts["live_observations"]},
            {"key": "under_testing", "label": "Under testing", "count": tab_counts["under_testing"]},
            {"key": "validated_edges", "label": "Validated edges", "count": tab_counts["validated_edges"]},
            {"key": "rejected_or_decayed", "label": "Disproved or faded", "count": tab_counts["rejected_or_decayed"]},
        ],
        "default_tab": default_tab,
        "spotlight": valid_relationships[0] if valid_relationships else None,
        "primary_blocker": (
            "Provider-backed historical score rows and forward outcomes are still missing."
            if score_tape_rows == 0 or label_count == 0
            else "No relationship has passed the frozen validation policy yet."
        ),
        "relationship_count": len(relationships),
        "relationships": relationships,
        "source_artifact_refs": [
            f"data/runtime/{PATTERN_SCORE_ARTIFACT}",
            f"data/runtime/{PATTERN_SCORE_TAPE_PROGRESS_ARTIFACT}",
            f"data/runtime/{FORWARD_LABEL_MANIFEST_ARTIFACT}",
            f"data/runtime/{STATISTICAL_BACKTEST_CHECKS_ARTIFACT}",
            f"data/runtime/{EDGE_SUMMARY_ARTIFACT}",
        ],
        **PUBLIC_AUTHORITY,
        "authority": authority_flags(),
    }


def _quantum_execution_mode(
    protocols: list[dict[str, Any]], comparisons: list[dict[str, Any]]
) -> tuple[str, str]:
    empirical = [row for row in comparisons if _empirical_comparison(row)]
    if any(row.get("hardware_used") is True for row in empirical):
        return "hardware", "Quantum hardware experiment completed"
    if empirical:
        if any("quantum" in str(row.get("method") or "") for row in empirical):
            return "quantum_inspired", "Quantum-inspired comparison completed without hardware"
        return "classical_nonlinear", "Nonlinear classical comparison completed"
    if protocols:
        return "not_run", "Experiment designed; empirical comparison not run"
    return "not_defined", "No quantum or nonlinear protocol is defined"


def _quantum_verdict(comparisons: list[dict[str, Any]]) -> tuple[str, str, str]:
    empirical = [row for row in comparisons if _empirical_comparison(row)]
    if not empirical:
        return (
            "not_measurable",
            "Qadam cannot yet measure whether nonlinear analysis adds value because no untouched holdout comparison exists.",
            "Under testing",
        )
    values = [safe_float(row.get("incremental_holdout_value")) for row in empirical]
    if any(value > 0 for value in values):
        return (
            "nonlinear_strengthened",
            "The nonlinear method added measured holdout value beyond the classical baseline.",
            "Integrated validation",
        )
    if all(row.get("classical_equal_or_better") is True for row in empirical):
        return (
            "classical_preferred",
            "The simpler classical model performed as well or better after penalties.",
            "Classical-only result",
        )
    return (
        "inconclusive",
        "The empirical comparison did not produce a reliable difference.",
        "Under testing",
    )


def build_quantum_review_projection(
    *,
    generated_at: str,
    pattern_discovery: dict[str, Any],
    protocols: list[dict[str, Any]],
    comparisons: list[dict[str, Any]],
    usefulness: dict[str, Any],
    overfit: dict[str, Any],
) -> dict[str, Any]:
    relationship_by_family = {
        str(row.get("strategy_family_id")): row
        for row in pattern_discovery.get("relationships", [])
        if row.get("strategy_family_id")
    }
    family_ids = sorted(
        {
            str(row.get("strategy_family_id"))
            for row in [*protocols, *comparisons]
            if row.get("strategy_family_id") in STRATEGY_COPY
        }
    )
    reviews: list[dict[str, Any]] = []
    empirical_total = 0
    hardware_total = 0
    for family in family_ids:
        copy = STRATEGY_COPY[family]
        family_protocols = [row for row in protocols if row.get("strategy_family_id") == family]
        family_comparisons = [row for row in comparisons if row.get("strategy_family_id") == family]
        empirical = [row for row in family_comparisons if _empirical_comparison(row)]
        empirical_total += len(empirical)
        hardware_total += sum(row.get("hardware_used") is True for row in empirical)
        mode, mode_label = _quantum_execution_mode(family_protocols, family_comparisons)
        verdict, verdict_text, returned_stage = _quantum_verdict(family_comparisons)
        relationship = relationship_by_family.get(family, {})
        method_rows = []
        for protocol in family_protocols:
            comparison = next(
                (
                    row
                    for row in family_comparisons
                    if row.get("experiment_id") == protocol.get("experiment_id")
                ),
                {},
            )
            method = str(protocol.get("method") or comparison.get("method") or "unknown")
            empirical_method = _empirical_comparison(comparison)
            method_rows.append(
                {
                    "experiment_id": protocol.get("experiment_id"),
                    "method": method,
                    "method_label": METHOD_COPY.get(method, method.replace("_", " ").title()),
                    "state": "comparison_complete" if empirical_method else "waiting_for_untouched_holdout",
                    "state_label": "Comparison complete" if empirical_method else "Not run; waiting for untouched holdout",
                    "classical_holdout_metric": comparison.get("classical_holdout_metric"),
                    "nonlinear_or_quantum_holdout_metric": comparison.get("nonlinear_or_quantum_holdout_metric"),
                    "incremental_holdout_value": comparison.get("incremental_holdout_value"),
                    "hardware_used": comparison.get("hardware_used") is True,
                    "fallback_declared": protocol.get("fallback") == "deterministic_classical_shadow",
                    "reproducibility_state": protocol.get("reproducibility_state"),
                }
            )
        reviews.append(
            {
                "review_id": stable_id("quantum-review", family),
                "pattern_id": relationship.get("pattern_id"),
                "strategy_family_id": family,
                "pattern_title": relationship.get("title") or copy["title"],
                "why_referred": copy["why_quantum"],
                "interaction_hypothesis": copy["interaction"],
                "method_family": "Quantum and nonlinear comparison",
                "execution_mode": mode,
                "execution_mode_label": mode_label,
                "hardware_used": any(row.get("hardware_used") is True for row in empirical),
                "classical_baseline": {
                    "name": next(
                        (
                            str(row.get("classical_baseline"))
                            for row in family_comparisons
                            if row.get("classical_baseline")
                        ),
                        "strategy-blind linear model",
                    ),
                    "holdout_metric": next(
                        (row.get("classical_holdout_metric") for row in empirical), None
                    ),
                },
                "quantum_or_nonlinear_result": {
                    "holdout_metric": next(
                        (row.get("nonlinear_or_quantum_holdout_metric") for row in empirical),
                        None,
                    ),
                    "incremental_holdout_value": next(
                        (row.get("incremental_holdout_value") for row in empirical), None
                    ),
                    "quantum_usefulness_score": next(
                        (row.get("quantum_usefulness_score") for row in empirical), None
                    ),
                },
                "complexity_penalty": next(
                    (row.get("complexity_penalty") for row in empirical), None
                ),
                "latency_penalty": next((row.get("latency_penalty") for row in empirical), None),
                "reliability_penalty": next(
                    (row.get("reliability_penalty") for row in empirical), None
                ),
                "net_usefulness": next(
                    (row.get("quantum_usefulness_score") for row in empirical), None
                ),
                "overfit_audit": {
                    "state": overfit.get("status") or "not_exported",
                    "summary": (
                        "The overfit protocol is defined, but no empirical experiment has run."
                        if not empirical
                        else "The empirical comparison must satisfy the recorded overfit audit."
                    ),
                },
                "verdict": verdict,
                "plain_english_verdict": verdict_text,
                "returned_to": "Pattern Discovery",
                "return_route": _route(
                    "patterns",
                    "findings",
                    "Pattern Discovery",
                    "Return to the integrated relationship record.",
                ),
                "next_destination": returned_stage,
                "blocked_by": (
                    ["No eligible untouched holdout exists for the final comparison."]
                    if not empirical
                    else []
                ),
                "freshness": _freshness(
                    _records_generated_at([*family_protocols, *family_comparisons]),
                    generated_at,
                    24 * 60 * 60,
                ),
                "protocol_count": len(family_protocols),
                "empirical_comparison_count": len(empirical),
                "methods": method_rows,
                "artifact_refs": [
                    f"data/runtime/{NONLINEAR_EXPERIMENT_ARTIFACT}",
                    f"data/runtime/{QUANTUM_COMPARISON_ARTIFACT}",
                    f"data/runtime/{QUANTUM_USEFULNESS_ARTIFACT}",
                    f"data/runtime/{NONLINEAR_OVERFIT_ARTIFACT}",
                ],
                **PUBLIC_AUTHORITY,
                "authority": authority_flags(),
            }
        )
    verdict_counts = defaultdict(int)
    for review in reviews:
        verdict_counts[str(review.get("verdict"))] += 1
    running_count = sum(
        str(row.get("status") or "").lower() in {"running", "in_progress", "submitted"}
        for row in protocols
    )
    latest = _records_generated_at([*protocols, *comparisons])
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_quantum_review_dashboard",
        "generated_at": generated_at,
        "status": "comparison_available" if empirical_total else "waiting_for_untouched_holdout",
        "headline": (
            "Quantum or nonlinear methods added measurable holdout value."
            if verdict_counts["nonlinear_strengthened"]
            else "Quantum usefulness is not measurable yet."
        ),
        "plain_english_summary": (
            "Qadam has defined the comparison protocol, but it cannot yet determine "
            "whether quantum or nonlinear methods improve on the classical baseline. "
            "No empirical quantum advantage has been measured."
            if empirical_total == 0
            else "Empirical classical-versus-quantum comparisons are available below."
        ),
        "purpose": (
            "Qadam uses this stage only when a candidate may depend on combinations, "
            "sequencing, regimes or nonlinear interactions that a simpler classical model "
            "could miss."
        ),
        "question": (
            "Did quantum or nonlinear analysis reveal useful predictive structure that the "
            "matched classical model missed?"
        ),
        "freshness": _freshness(latest, generated_at, 24 * 60 * 60),
        "current_method_state": {
            "hardware_used": hardware_total > 0,
            "hardware_completed_count": hardware_total,
            "simulator_completed_count": 0,
            "fallback_declared_count": sum(
                row.get("fallback") == "deterministic_classical_shadow" for row in protocols
            ),
            "plain_english": (
                "No quantum hardware or simulator result has been recorded; the current "
                "records define classical fallback protocols only."
                if empirical_total == 0
                else "Method truth is shown on every completed comparison."
            ),
        },
        "funnel": [
            {"key": "referred", "label": "Patterns referred", "count": len(reviews)},
            {"key": "baseline", "label": "Classical baselines defined", "count": len(reviews)},
            {"key": "protocols", "label": "Experiment protocols", "count": len(protocols)},
            {"key": "empirical", "label": "Empirical comparisons", "count": empirical_total},
            {"key": "strengthened", "label": "Nonlinear strengthened", "count": verdict_counts["nonlinear_strengthened"]},
            {"key": "returned", "label": "Verdicts returned", "count": sum(review["verdict"] != "not_measurable" for review in reviews)},
        ],
        "empirical_comparison_count": empirical_total,
        "defined_protocol_count": len(protocols),
        "running_count": running_count,
        "strengthened_count": verdict_counts["nonlinear_strengthened"],
        "classical_preferred_count": verdict_counts["classical_preferred"],
        "weakened_count": verdict_counts["weakened"],
        "inconclusive_count": verdict_counts["inconclusive"],
        "waiting_count": verdict_counts["not_measurable"],
        "review_count": len(reviews),
        "reviews": reviews,
        "protocols": [method for review in reviews for method in review["methods"]],
        "overfit_state": overfit.get("status") or "not_exported",
        "quantum_usefulness_score": usefulness.get("quantum_usefulness_score"),
        "boundary": (
            "Quantum Review can strengthen, weaken or leave a research relationship "
            "unresolved. It cannot create a strategy, approve risk, submit an order or "
            "grant paper proof ledger credit."
        ),
        "source_artifact_refs": [
            f"data/runtime/{NONLINEAR_EXPERIMENT_ARTIFACT}",
            f"data/runtime/{QUANTUM_COMPARISON_ARTIFACT}",
            f"data/runtime/{QUANTUM_USEFULNESS_ARTIFACT}",
            f"data/runtime/{NONLINEAR_OVERFIT_ARTIFACT}",
        ],
        **PUBLIC_AUTHORITY,
        "authority": authority_flags(),
    }


def build_pattern_dashboard_views(
    settings: Settings | None = None, *, generated_at: str | None = None
) -> dict[str, dict[str, Any]]:
    runtime = runtime_dir(settings)
    generated = generated_at or now_iso()
    scores = read_jsonl(runtime / PATTERN_SCORE_ARTIFACT)
    edges = read_jsonl(runtime / EDGE_REGISTRY_ARTIFACT)
    score_tape = read_json(runtime / PATTERN_SCORE_TAPE_PROGRESS_ARTIFACT)
    forward_labels = read_json(runtime / FORWARD_LABEL_MANIFEST_ARTIFACT)
    backtest = read_json(runtime / STATISTICAL_BACKTEST_CHECKS_ARTIFACT)
    edge_summary = read_json(runtime / EDGE_SUMMARY_ARTIFACT)
    backfill = read_json(runtime / BACKFILL_SUMMARY_ARTIFACT)
    protocols = read_jsonl(runtime / NONLINEAR_EXPERIMENT_ARTIFACT)
    comparisons = read_jsonl(runtime / QUANTUM_COMPARISON_ARTIFACT)
    usefulness = read_json(runtime / QUANTUM_USEFULNESS_ARTIFACT)
    overfit = read_json(runtime / NONLINEAR_OVERFIT_ARTIFACT)
    pattern_discovery = build_pattern_discovery_projection(
        generated_at=generated,
        scores=scores,
        edges=edges,
        score_tape=score_tape,
        forward_labels=forward_labels,
        backtest=backtest,
        edge_summary=edge_summary,
        backfill=backfill,
        comparisons=comparisons,
    )
    quantum_review = build_quantum_review_projection(
        generated_at=generated,
        pattern_discovery=pattern_discovery,
        protocols=protocols,
        comparisons=comparisons,
        usefulness=usefulness,
        overfit=overfit,
    )
    return {
        "pattern_discovery": pattern_discovery,
        "quantum_review": quantum_review,
    }


def validate_pattern_discovery(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("artifact_type") != "qadam_pattern_discovery_dashboard":
        errors.append("pattern_discovery_artifact_type_invalid")
    if payload.get("relationship_count") != len(payload.get("relationships") or []):
        errors.append("pattern_discovery_relationship_count_mismatch")
    pattern_ids = [row.get("pattern_id") for row in payload.get("relationships") or []]
    if len(pattern_ids) != len(set(pattern_ids)):
        errors.append("pattern_discovery_duplicate_relationship_identity")
    for row in payload.get("relationships") or []:
        pattern_id = row.get("pattern_id") or "missing"
        for field in (
            "title",
            "stage",
            "source_signal",
            "target_market",
            "current_stage",
            "next_destination",
            "advance_when",
            "failure_destination",
            "freshness",
        ):
            if not row.get(field):
                errors.append(f"pattern_discovery_{pattern_id}_missing_{field}")
        if row.get("raw_pattern_score_is_probability") is not False:
            errors.append(f"pattern_discovery_{pattern_id}_score_probability_violation")
        if row.get("stage") == "validated_edge" and not row.get("historical_evidence", {}).get(
            "validated_edge"
        ):
            errors.append(f"pattern_discovery_{pattern_id}_validated_without_evidence")
        errors.extend(validate_authority(row.get("authority", {}), prefix=f"pattern_{pattern_id}"))
    bullets = payload.get("qualitative_analysis", {}).get("bullets") or []
    if payload.get("relationships") and not bullets:
        errors.append("pattern_discovery_recent_analysis_bullets_missing")
    for bullet in bullets:
        ratio = bullet.get("fresh_source_ratio")
        if not isinstance(ratio, (int, float)) or not 0.0 <= float(ratio) <= 1.0:
            errors.append("pattern_discovery_recent_analysis_freshness_ratio_invalid")
    for field, expected in PUBLIC_AUTHORITY.items():
        if payload.get(field) is not expected:
            errors.append(f"pattern_discovery_unsafe_{field}")
    errors.extend(validate_authority(payload.get("authority", {}), prefix="pattern_discovery"))
    return unique_errors(errors)


def validate_quantum_review(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("artifact_type") != "qadam_quantum_review_dashboard":
        errors.append("quantum_review_artifact_type_invalid")
    empirical_count = sum(
        row.get("empirical_comparison_count", 0) for row in payload.get("reviews") or []
    )
    if payload.get("empirical_comparison_count") != empirical_count:
        errors.append("quantum_review_empirical_count_mismatch")
    review_ids = [row.get("review_id") for row in payload.get("reviews") or []]
    if len(review_ids) != len(set(review_ids)):
        errors.append("quantum_review_duplicate_review_identity")
    for row in payload.get("reviews") or []:
        review_id = row.get("review_id") or "missing"
        for field in (
            "pattern_title",
            "why_referred",
            "interaction_hypothesis",
            "execution_mode",
            "verdict",
            "plain_english_verdict",
            "returned_to",
            "next_destination",
        ):
            if not row.get(field):
                errors.append(f"quantum_review_{review_id}_missing_{field}")
        if row.get("hardware_used") is True and row.get("execution_mode") != "hardware":
            errors.append(f"quantum_review_{review_id}_hardware_mode_mismatch")
        if row.get("verdict") == "nonlinear_strengthened" and row.get("net_usefulness") is None:
            errors.append(f"quantum_review_{review_id}_strengthened_without_metric")
        errors.extend(validate_authority(row.get("authority", {}), prefix=f"quantum_{review_id}"))
    if payload.get("empirical_comparison_count") == 0 and payload.get("status") == "comparison_available":
        errors.append("quantum_review_completed_without_empirical_comparison")
    for field, expected in PUBLIC_AUTHORITY.items():
        if payload.get(field) is not expected:
            errors.append(f"quantum_review_unsafe_{field}")
    errors.extend(validate_authority(payload.get("authority", {}), prefix="quantum_review"))
    return unique_errors(errors)


def validate_pattern_dashboard_views(views: dict[str, dict[str, Any]]) -> list[str]:
    return unique_errors(
        [
            *validate_pattern_discovery(views.get("pattern_discovery", {})),
            *validate_quantum_review(views.get("quantum_review", {})),
        ]
    )
