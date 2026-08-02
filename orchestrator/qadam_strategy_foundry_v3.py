"""OR-11 Strategy Foundry V3.

Only durable OR-10 edge records may become V3 strategy hypotheses. The
resulting records are research objects for Akber review, never trade
candidates, qualified setups, approvals, or orders.
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from datetime import timedelta
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_experimental_paper_policy import (
    BOUNDED_EXPERIMENTAL_TIER,
    DISCOVERY_MICRO_TIER,
    EXPERIMENTAL_UNVALIDATED,
    POLICY_VERSION as EXPERIMENTAL_POLICY_VERSION,
    RESEARCH_ONLY,
    VALIDATED_PAPER_STRATEGY,
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
from orchestrator.qadam_wave_b_common import (
    parse_timestamp,
    record_set_hash,
    safe_float,
    safe_int,
    stable_id,
)

SCHEMA_VERSION = "qadam_strategy_foundry_v3.v2"
PHASE_ID = "OR-11"

PRIMARY_ARTIFACT = "qadam_strategy_foundry_v3.json"
HYPOTHESES_ARTIFACT = "qadam_strategy_hypotheses_v3.jsonl"
REJECTIONS_ARTIFACT = "qadam_strategy_hypothesis_rejections_v3.jsonl"
DASHBOARD_ARTIFACT = "qadam_strategy_foundry_v3_dashboard_summary.json"
CHECK_ARTIFACT = "qadam_strategy_foundry_v3_checks.json"

EDGE_REGISTRY_ARTIFACT = "qadam_edge_registry.jsonl"
EDGE_SUMMARY_ARTIFACT = "qadam_edge_registry_summary.json"
STRATEGY_MAP_ARTIFACT = "qadam_strategy_evidence_map_v3.json"
PATTERN_SCORES_ARTIFACT = "qadam_pattern_score_v3_records.jsonl"
EXPERIMENTAL_POLICY_ARTIFACT = "qadam_experimental_paper_policy.json"
POWER_MARKET_STRATEGY_ARTIFACT = "qadam_power_market_strategy_registry.json"
POWER_MARKET_SCORES_ARTIFACT = "qadam_power_market_pattern_scores.jsonl"
POWER_MARKET_CHECK_ARTIFACT = "qadam_power_market_edge_engine_checks.json"

ALLOWED_EDGE_CLASSES = {"validated_research_edge", "exploratory_research_edge"}
ALLOWED_HYPOTHESIS_STATES = {"ready_for_akber_review", "shadow_only"}
ALLOWED_EDGE_REGISTRY_STATUSES = {
    "edge_registry_complete_with_validated_edges",
    "edge_registry_complete_no_validated_edge",
}
REQUIRED_HYPOTHESIS_FIELDS = (
    "edge_lineage",
    "research_goal_lineage",
    "candidate_identity_material",
    "strategy_mapping",
    "instrument_proxy_mapping",
    "direction_horizon",
    "catalyst_confirmation",
    "entry_concept",
    "invalidation_exit",
    "risk_concept",
    "expected_edge_range",
    "known_failure_modes",
    "blocker_state",
    "paperability",
    "freshness",
)


def _strategy_by_id(strategy_map: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = strategy_map.get("strategies")
    if not isinstance(rows, list):
        return {}
    return {
        str(row.get("strategy_family_id")): row
        for row in rows
        if isinstance(row, dict) and row.get("strategy_family_id")
    }


def _edge_registry_lineage(
    edges: list[dict[str, Any]],
    edge_summary: dict[str, Any],
    strategy_map: dict[str, Any],
) -> dict[str, Any]:
    strategies = strategy_map.get("strategies")
    strategy_rows = strategies if isinstance(strategies, list) else []
    return {
        "edge_registry_artifact": EDGE_REGISTRY_ARTIFACT,
        "edge_registry_summary_artifact": EDGE_SUMMARY_ARTIFACT,
        "strategy_evidence_map_artifact": STRATEGY_MAP_ARTIFACT,
        "edge_registry_schema_version": edge_summary.get("schema_version"),
        "edge_registry_generated_at": edge_summary.get("generated_at"),
        "edge_registry_status": edge_summary.get("status"),
        "edge_registry_record_set_hash": record_set_hash(edges),
        "strategy_evidence_map_record_set_hash": record_set_hash(strategy_rows),
        "backtest_run_id": edge_summary.get("backtest_run_id"),
        "backtest_result_record_set_hash": edge_summary.get("backtest_result_record_set_hash"),
        "backtest_fold_record_set_hash": edge_summary.get("backtest_fold_record_set_hash"),
        "quantum_run_id": edge_summary.get("quantum_run_id"),
        "complete": True,
    }


def _foundry_input_errors(
    edges: list[dict[str, Any]],
    edge_summary: dict[str, Any],
    strategy_map: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    strategies = strategy_map.get("strategies")
    strategy_rows = strategies if isinstance(strategies, list) else []
    strategy_ids = [
        str(row.get("strategy_family_id") or "") for row in strategy_rows if isinstance(row, dict)
    ]
    edge_ids = [str(edge.get("edge_id") or "") for edge in edges]

    if edge_summary.get("status") not in ALLOWED_EDGE_REGISTRY_STATUSES:
        errors.append("or10_edge_registry_status_not_complete")
    if edge_summary.get("implementation_complete") is not True:
        errors.append("or10_edge_registry_implementation_not_complete")
    if safe_int(edge_summary.get("edge_count"), -1) != len(edges):
        errors.append("or10_edge_registry_count_mismatch")
    if edge_summary.get("status") == "edge_registry_complete_no_validated_edge" and edges:
        errors.append("or10_no_edge_status_contains_edges")
    if not edge_summary.get("backtest_run_id"):
        errors.append("or10_backtest_run_lineage_missing")
    if not edge_summary.get("backtest_result_record_set_hash"):
        errors.append("or10_backtest_result_hash_missing")
    if not edge_summary.get("backtest_fold_record_set_hash"):
        errors.append("or10_backtest_fold_hash_missing")
    if not strategy_rows:
        errors.append("or10_strategy_evidence_map_empty")
    if safe_int(strategy_map.get("strategy_count"), -1) != len(strategy_rows):
        errors.append("or10_strategy_evidence_map_count_mismatch")
    if any(not strategy_id for strategy_id in strategy_ids) or len(strategy_ids) != len(
        set(strategy_ids)
    ):
        errors.append("or10_strategy_family_id_missing_or_duplicate")
    if any(not edge_id for edge_id in edge_ids) or len(edge_ids) != len(set(edge_ids)):
        errors.append("or10_edge_id_missing_or_duplicate")
    for edge in edges:
        edge_id = str(edge.get("edge_id") or "unknown")
        if edge.get("promotion_class") not in ALLOWED_EDGE_CLASSES:
            errors.append(f"or10_edge_promotion_class_invalid:{edge_id}")
        if edge.get("backtest_run_id") != edge_summary.get("backtest_run_id"):
            errors.append(f"or10_edge_backtest_run_mismatch:{edge_id}")
        if not edge.get("fold_ids") or not isinstance(edge.get("dataset_hashes"), dict):
            errors.append(f"or10_edge_empirical_lineage_incomplete:{edge_id}")
    errors.extend(validate_authority(edge_summary.get("authority", {}), prefix="or10_summary"))
    errors.extend(validate_authority(strategy_map.get("authority", {}), prefix="or10_strategy_map"))
    return unique_errors(errors)


def _best_strategy_id(edge: dict[str, Any]) -> tuple[str | None, float]:
    explicit = edge.get("strategy_family_id")
    vector = edge.get("strategy_fit_vector")
    if explicit:
        fit = safe_float(vector.get(explicit)) if isinstance(vector, dict) else 0.0
        return str(explicit), fit
    if not isinstance(vector, dict) or not vector:
        return None, 0.0
    ranked = sorted(
        ((str(key), safe_float(value)) for key, value in vector.items()),
        key=lambda item: (-item[1], item[0]),
    )
    return ranked[0] if ranked and ranked[0][1] > 0 else (None, 0.0)


def _instrument_mapping(edge: dict[str, Any], strategy: dict[str, Any]) -> dict[str, Any]:
    instrument = str(edge.get("instrument") or "")
    contribution = strategy.get("instrument_contribution")
    rows = contribution.get("instruments") if isinstance(contribution, dict) else []
    rows = rows if isinstance(rows, list) else []
    paperable = [
        str(row.get("symbol"))
        for row in rows
        if isinstance(row, dict) and row.get("symbol") and row.get("paper_route_available") is True
    ]
    best = strategy.get("best_observed_rejected_result")
    best = best if isinstance(best, dict) else {}
    historically_best = str(best.get("instrument") or "")
    preferred_by_research_instrument = {
        "CL=F": ("USO", "BNO", "XLE"),
        "SI=F": ("SLV", "SIL", "GLD"),
    }
    preferred = preferred_by_research_instrument.get(instrument, ())
    ranked_paperable = (
        [historically_best]
        if historically_best and historically_best in paperable
        else []
    )
    ranked_paperable.extend(
        symbol for symbol in preferred if symbol in paperable and symbol not in ranked_paperable
    )
    ranked_paperable.extend(symbol for symbol in paperable if symbol not in ranked_paperable)
    proxy = instrument if instrument in paperable else (ranked_paperable[0] if ranked_paperable else None)
    return {
        "observed_instrument": instrument,
        "execution_proxy": proxy,
        "observed_instrument_directly_paperable": instrument in paperable,
        "paperable_proxy_symbols": paperable,
        "ranked_paperable_proxy_symbols": ranked_paperable,
        "proxy_selection_policy": "closest_liquid_guarded_paper_proxy_v1",
        "proxy_basis": "direct" if instrument in paperable else "strategy_family_proxy",
        "proxy_review_required": proxy is not None and proxy != instrument,
        "paper_order_allowed": False,
    }


def _normalise_experimental_direction(value: Any) -> str | None:
    """Translate only explicit directional language into an executable side."""

    direction = str(value or "").strip().lower()
    if direction in {"buy", "long"} or direction.startswith("upside_"):
        return "long"
    if direction in {"sell", "short"} or direction.startswith("downside_"):
        return "short"
    return None


def _experimental_relationship_key(score: dict[str, Any]) -> tuple[Any, ...]:
    source_keys = sorted(
        {
            str(row.get("source_key"))
            for row in score.get("feature_inputs", [])
            if isinstance(row, dict)
            and row.get("fresh") is True
            and row.get("source_key")
            and (
                row.get("quorum_eligible") is True
                or row.get("mapping_class") == "causal_strategy_mapping"
            )
        }
    )
    return (
        str(score.get("strategy_family_id") or ""),
        _normalise_experimental_direction(score.get("direction_hypothesis")),
        str(score.get("horizon_hypothesis") or "3d_forward"),
        tuple(source_keys),
    )


def _select_experimental_pattern_variants(
    pattern_rows: list[dict[str, Any]],
    strategies: dict[str, dict[str, Any]],
    policy: dict[str, Any],
) -> tuple[set[str], set[str]]:
    """Choose one execution proxy for each distinct source-direction relationship."""

    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for score in pattern_rows:
        strategy = strategies.get(str(score.get("strategy_family_id") or ""))
        if not experimental_pattern_admission(score, strategy, policy)["admitted"]:
            continue
        groups.setdefault(_experimental_relationship_key(score), []).append(score)

    selected: set[str] = set()
    redundant: set[str] = set()
    for rows in groups.values():
        def rank(score: dict[str, Any]) -> tuple[Any, ...]:
            strategy = strategies.get(str(score.get("strategy_family_id") or ""), {})
            best = strategy.get("best_observed_rejected_result")
            best = best if isinstance(best, dict) else {}
            best_instrument = str(best.get("instrument") or "")
            mapping = _instrument_mapping(score, strategy)
            instrument = str(score.get("instrument") or "")
            return (
                -int(bool(best_instrument and instrument == best_instrument)),
                -int(mapping.get("observed_instrument_directly_paperable") is True),
                -safe_float(score.get("raw_pattern_score")),
                instrument,
                str(score.get("score_id") or ""),
            )

        ordered = sorted(rows, key=rank)
        winner_id = str(ordered[0].get("score_id") or "")
        if winner_id:
            selected.add(winner_id)
        redundant.update(
            str(row.get("score_id") or "")
            for row in ordered[1:]
            if row.get("score_id")
        )
    return selected, redundant


def _expiry(generated_at: str, horizon: str) -> str:
    created = parse_timestamp(generated_at)
    if created is None:
        raise ValueError("generated_at_invalid")
    horizon_days = {
        "1d_forward": 1,
        "3d_forward": 3,
        "5d_forward": 5,
        "10d_forward": 10,
        "20d_forward": 20,
        "event_expiry": 7,
    }
    return (created + timedelta(days=horizon_days.get(horizon, 3))).isoformat()


def hypothesis_rejection_reasons(
    edge: dict[str, Any], strategy: dict[str, Any] | None
) -> list[str]:
    reasons: list[str] = []
    if not edge.get("edge_id"):
        reasons.append("missing_edge_registry_reference")
    if edge.get("promotion_class") not in ALLOWED_EDGE_CLASSES:
        reasons.append("unsupported_edge_promotion_class")
    for field in (
        "source_feature_definition",
        "instrument",
        "direction",
        "horizon",
        "score_version",
        "label_version",
        "backtest_run_id",
    ):
        if not edge.get(field):
            reasons.append(f"missing_edge_field:{field}")
    if not edge.get("fold_ids"):
        reasons.append("missing_edge_field:fold_ids")
    if not isinstance(edge.get("dataset_hashes"), dict) or not edge.get("dataset_hashes"):
        reasons.append("missing_edge_field:dataset_hashes")
    if edge.get("decay_state") in {"stale", "retired", "invalidated"}:
        reasons.append("stale_or_retired_edge")
    net_expectancy = edge.get("net_expectancy")
    if net_expectancy is None:
        reasons.append("expected_net_return_after_costs_missing")
    elif safe_float(net_expectancy) <= 0:
        reasons.append("non_positive_expected_return_after_costs")
    if strategy is None:
        reasons.append("unsupported_strategy_mapping")
    else:
        strategy_id, fit_score = _best_strategy_id(edge)
        if strategy_id != strategy.get("strategy_family_id") or fit_score <= 0:
            reasons.append("strategy_fit_missing_or_non_positive")
        if _instrument_mapping(edge, strategy).get("execution_proxy") is None:
            reasons.append("non_paperable_no_execution_proxy")
    direction = str(edge.get("direction") or "").lower()
    if direction in {"", "unknown", "undetermined", "none"}:
        reasons.append("direction_not_actionable")
    return unique_errors(reasons)


def build_strategy_hypothesis(
    edge: dict[str, Any],
    strategy: dict[str, Any],
    *,
    generated_at: str,
    edge_registry_lineage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a trade-shaped research hypothesis from one eligible edge."""

    reasons = hypothesis_rejection_reasons(edge, strategy)
    if reasons:
        raise ValueError("edge_not_hypothesis_eligible:" + ",".join(reasons))
    edge_id = str(edge["edge_id"])
    strategy_id, fit_score = _best_strategy_id(edge)
    if strategy_id is None:
        raise ValueError("strategy_mapping_missing")
    instrument_mapping = _instrument_mapping(edge, strategy)
    instrument = str(edge["instrument"])
    direction = str(edge["direction"])
    horizon = str(edge["horizon"])
    research_goal_id = stable_id(
        "research-goal-v3", edge_id, strategy_id, instrument, direction, horizon
    )
    identity_id = stable_id(
        "strategy-hypothesis-identity-v3",
        research_goal_id,
        edge_id,
        instrument,
        instrument_mapping["execution_proxy"],
        direction,
        horizon,
    )
    source_packet_id = stable_id(
        "strategy-source-packet-v3",
        edge_id,
        edge.get("source_feature_definition"),
        edge.get("dataset_hashes"),
    )
    invalidation_id = stable_id("strategy-invalidation-v3", identity_id)
    risk_concept_id = stable_id("strategy-risk-concept-v3", identity_id)
    hypothesis_id = stable_id("strategy-hypothesis-v3", identity_id)
    exploratory = edge.get("promotion_class") == "exploratory_research_edge"
    confidence = edge.get("confidence_distribution")
    expected_range = {
        "gross_expectancy": edge.get("gross_expectancy"),
        "net_expectancy": edge.get("net_expectancy"),
        "confidence_distribution": confidence,
        "range_is_research_estimate_only": True,
        "not_a_return_guarantee": True,
    }
    record = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_strategy_hypothesis_v3",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "hypothesis_id": hypothesis_id,
        "evidence_class": (
            RESEARCH_ONLY if exploratory else VALIDATED_PAPER_STRATEGY
        ),
        "paper_experiment_purpose": None,
        "hypothesis_state": "shadow_only" if exploratory else "ready_for_akber_review",
        "edge_lineage": {
            "edge_id": edge_id,
            "promotion_class": edge.get("promotion_class"),
            "edge_registry_reference": edge_registry_lineage
            or {
                "edge_registry_artifact": EDGE_REGISTRY_ARTIFACT,
                "edge_registry_summary_artifact": EDGE_SUMMARY_ARTIFACT,
                "edge_registry_record_set_hash": None,
                "complete": False,
            },
            "score_version": edge.get("score_version"),
            "label_version": edge.get("label_version"),
            "backtest_run_id": edge.get("backtest_run_id"),
            "fold_ids": edge.get("fold_ids", []),
            "dataset_hashes": edge.get("dataset_hashes", {}),
            "applied_learning_version_ids": edge.get("applied_learning_version_ids", []),
            "stage1_learning_input_version": edge.get("stage1_learning_input_version"),
        },
        "research_goal_lineage": {
            "research_goal_id": research_goal_id,
            "origin_edge_id": edge_id,
            "origin_phase": "OR-10",
            "foundry_phase": PHASE_ID,
            "target_strategy_family": strategy_id,
            "strategy_evidence_map_record_set_hash": (edge_registry_lineage or {}).get(
                "strategy_evidence_map_record_set_hash"
            ),
            "evidence_chain": [
                "OR-8 frozen walk-forward backtest",
                "OR-9 incremental nonlinear and quantum comparison",
                "OR-10 durable edge registry admission",
                "OR-11 research-only strategy formation",
            ],
            "complete": True,
        },
        "candidate_identity_material": {
            "candidate_identity_id": identity_id,
            "identity_type": "research_hypothesis_identity_not_trade_candidate",
            "research_goal_id": research_goal_id,
            "strategy_family_id": strategy_id,
            "origin_edge_id": edge_id,
            "observed_instrument": instrument,
            "paperable_proxy_expression": instrument_mapping["execution_proxy"],
            "direction": direction,
            "time_window": horizon,
            "thesis": (
                f"The admitted {edge.get('source_feature_definition')} relationship may "
                f"support a {direction} research expression in {instrument} over {horizon}."
            ),
            "source_packet_id": source_packet_id,
            "source_recipe_fingerprint": stable_id(
                "strategy-source-recipe-v3",
                strategy_id,
                edge.get("source_feature_definition"),
                instrument,
            ),
            "invalidation_id": invalidation_id,
            "risk_concept_id": risk_concept_id,
            "identity_fields": [
                "research_goal_id",
                "edge_id",
                "instrument",
                "execution_proxy",
                "direction",
                "horizon",
            ],
            "not_trade_candidate": True,
            "not_idempotency_key_for_orders": True,
            "trade_candidate_created": False,
            "order_idempotency_key_created": False,
        },
        "strategy_mapping": {
            "strategy_family_id": strategy_id,
            "strategy_label": strategy.get("label") or strategy_id,
            "fit_score": fit_score,
            "fit_is_research_context_only": True,
        },
        "instrument_proxy_mapping": instrument_mapping,
        "direction_horizon": {
            "direction": direction,
            "horizon": horizon,
            "regime": edge.get("regime"),
        },
        "catalyst_confirmation": {
            "catalyst": edge.get("source_feature_definition"),
            "confirmation_required": [
                "fresh independent source confirmation",
                "current price and volatility context",
                "volume or flow confirmation",
                "positive expected return after costs",
            ],
            "confirmation_complete": False,
        },
        "entry_concept": {
            "summary": (
                "Consider the mapped paper proxy only after Akber confirms that the "
                "historical relationship is active in current market conditions."
            ),
            "entry_authorized": False,
        },
        "invalidation_exit": {
            "invalidation_conditions": edge.get("falsifiers", [])
            or [
                "source relationship reverses",
                "market confirmation fails",
                "expected return turns non-positive after costs",
            ],
            "exit_conditions": [
                "hypothesis horizon completes",
                "invalidation condition occurs",
                "risk or liquidity state deteriorates",
            ],
            "exit_order_created": False,
        },
        "risk_concept": {
            "maximum_loss_must_be_derived_from_invalidation": True,
            "liquidity_and_spread_required": True,
            "portfolio_correlation_required": True,
            "position_size": None,
            "risk_approval_created": False,
        },
        "expected_edge_range": expected_range,
        "known_failure_modes": edge.get("retirement_conditions", [])
        or [
            "one-regime overfit",
            "source duplication",
            "transaction costs erase the edge",
            "signal decays before execution",
        ],
        "blocker_state": {
            "state": "exploratory_edge_shadow_only" if exploratory else "akber_review_required",
            "blockers": ["exploratory_edge_cannot_leave_shadow"] if exploratory else [],
            "router_eligible": False,
        },
        "paperability": {
            "state": (
                "direct_proxy_available_review_required"
                if instrument_mapping["observed_instrument_directly_paperable"]
                else "approved_proxy_available_review_required"
            ),
            "execution_proxy": instrument_mapping["execution_proxy"],
            "paper_route_required": "guarded_alpaca_paper_via_paperops",
            "paper_order_allowed": False,
        },
        "freshness": {
            "created_at": generated_at,
            "expires_at": _expiry(generated_at, horizon),
            "latest_supporting_sample": edge.get("latest_supporting_sample"),
            "expiry_requires_new_evidence": True,
        },
        "qualitative_reasoning": {
            "summary": (
                f"The {strategy.get('label') or strategy_id} family is the closest fit for "
                f"the {instrument} edge. Current confirmation still belongs to Akber and shadow review."
            ),
            "cited_evidence_refs": [edge_id, research_goal_id],
            "llm_numeric_proof_allowed": False,
            "llm_trade_authority": False,
        },
        "akber_review_allowed": not exploratory,
        "qualified_setup_created": False,
        "trade_candidate_created": False,
        "paper_order_created": False,
        "proof_credit_allowed": False,
        "authority": authority_flags(),
    }
    return record


def _bounded_experimental_rejection_reasons(
    score: dict[str, Any],
    strategy: dict[str, Any] | None,
    policy: dict[str, Any],
) -> list[str]:
    """Return reasons a score cannot enter the original bounded lane."""

    reasons: list[str] = []
    admission = policy.get("experimental_admission", {})
    minimum_score = safe_float(admission.get("minimum_research_score"), 0.50)
    if policy.get("policy_version") != EXPERIMENTAL_POLICY_VERSION:
        reasons.append("experimental_policy_not_frozen")
    if safe_float(score.get("raw_pattern_score")) < minimum_score:
        reasons.append("research_score_below_experimental_minimum")
    if score.get("confidence_state") != "score_ready_for_tape":
        reasons.append("pattern_score_not_ready_for_tape")
    if score.get("negative_control") is True:
        reasons.append("negative_control_cannot_form_hypothesis")
    if score.get("missing_critical_features"):
        reasons.append("decision_critical_pattern_features_missing")
    if _normalise_experimental_direction(score.get("direction_hypothesis")) is None:
        reasons.append("direction_not_actionable")
    fresh_clusters = {
        str(row.get("independence_cluster_id"))
        for row in score.get("feature_inputs", [])
        if isinstance(row, dict)
        and row.get("fresh") is True
        and row.get("quorum_eligible") is True
        and row.get("independence_cluster_id")
    }
    minimum_families = safe_int(
        admission.get("minimum_independent_source_families"), 2
    )
    if len(fresh_clusters) < minimum_families:
        reasons.append("independent_fresh_source_quorum_not_met")
    if strategy is None:
        reasons.append("unsupported_strategy_mapping")
        return unique_errors(reasons)
    if _instrument_mapping(score, strategy).get("execution_proxy") is None:
        reasons.append("non_paperable_no_execution_proxy")
    best = strategy.get("best_observed_rejected_result")
    best = best if isinstance(best, dict) else {}
    if safe_float(best.get("mean_net_return")) <= 0:
        reasons.append("positive_provisional_expectancy_after_costs_missing")
    if best.get("not_a_validated_expectancy") is not True:
        reasons.append("provisional_expectancy_boundary_missing")
    return unique_errors(reasons)


def _discovery_micro_rejection_reasons(
    score: dict[str, Any],
    strategy: dict[str, Any] | None,
    policy: dict[str, Any],
) -> list[str]:
    """Apply the smaller discovery lane without converting absence into evidence."""

    reasons: list[str] = []
    admission = policy.get("discovery_micro_admission", {})
    if policy.get("policy_version") != EXPERIMENTAL_POLICY_VERSION:
        reasons.append("experimental_policy_not_frozen")
    if admission.get("enabled") is not True:
        reasons.append("discovery_micro_tier_disabled")
    if safe_float(score.get("raw_pattern_score")) < safe_float(
        admission.get("minimum_research_score"), 0.45
    ):
        reasons.append("research_score_below_discovery_micro_minimum")
    if score.get("negative_control") is True:
        reasons.append("negative_control_cannot_form_hypothesis")
    missing = set(str(value) for value in score.get("missing_critical_features", []))
    if missing - {"fresh_source_quorum"}:
        reasons.append("discovery_micro_decision_critical_features_missing")
    if score.get("confidence_state") not in {
        "score_ready_for_tape",
        "blocked_missing_critical_features",
    }:
        reasons.append("pattern_score_not_ready_for_discovery_micro_review")
    if _normalise_experimental_direction(score.get("direction_hypothesis")) is None:
        reasons.append("direction_not_actionable")

    trust_floor = safe_float(admission.get("minimum_catalyst_source_trust"), 0.70)
    catalyst_rows = [
        row
        for row in score.get("feature_inputs", [])
        if isinstance(row, dict)
        and row.get("fresh") is True
        and safe_float(row.get("trust_score")) >= trust_floor
        and (
            admission.get("causal_source_mapping_required") is not True
            or row.get("mapping_class") == "causal_strategy_mapping"
        )
        and row.get("independence_cluster_id")
        and row.get("source_key")
        and row.get("provenance")
    ]
    minimum_catalysts = safe_int(admission.get("minimum_fresh_catalyst_sources"), 1)
    if len({str(row.get("independence_cluster_id")) for row in catalyst_rows}) < minimum_catalysts:
        reasons.append("discovery_micro_fresh_catalyst_not_met")

    features = score.get("features") if isinstance(score.get("features"), dict) else {}
    required_market_features = (
        "current_market_price",
        "volatility_context",
        "volume_or_flow_context",
    )
    if any(safe_float(features.get(field)) < 1.0 for field in required_market_features):
        reasons.append("discovery_micro_independent_market_confirmation_missing")
    if strategy is None:
        reasons.append("unsupported_strategy_mapping")
        return unique_errors(reasons)
    if _instrument_mapping(score, strategy).get("execution_proxy") is None:
        reasons.append("non_paperable_no_execution_proxy")
    return unique_errors(reasons)


def experimental_pattern_admission(
    score: dict[str, Any],
    strategy: dict[str, Any] | None,
    policy: dict[str, Any],
) -> dict[str, Any]:
    """Prefer the smallest evidence-collection tier for every unvalidated pattern."""

    micro_reasons = _discovery_micro_rejection_reasons(score, strategy, policy)
    if not micro_reasons:
        bounded_reasons = _bounded_experimental_rejection_reasons(score, strategy, policy)
        return {
            "admitted": True,
            "tier": DISCOVERY_MICRO_TIER,
            "reasons": [],
            "bounded_tier_reasons": bounded_reasons,
        }
    bounded_reasons = _bounded_experimental_rejection_reasons(score, strategy, policy)
    if not bounded_reasons:
        return {
            "admitted": True,
            "tier": BOUNDED_EXPERIMENTAL_TIER,
            "reasons": [],
            "discovery_micro_tier_reasons": micro_reasons,
        }
    return {
        "admitted": False,
        "tier": None,
        "reasons": unique_errors([*bounded_reasons, *micro_reasons]),
        "bounded_tier_reasons": bounded_reasons,
        "discovery_micro_tier_reasons": micro_reasons,
    }


def experimental_pattern_rejection_reasons(
    score: dict[str, Any],
    strategy: dict[str, Any] | None,
    policy: dict[str, Any],
) -> list[str]:
    """Return no reasons when either bounded experimental tier is admissible."""

    return experimental_pattern_admission(score, strategy, policy)["reasons"]


def build_experimental_strategy_hypothesis(
    score: dict[str, Any],
    strategy: dict[str, Any],
    *,
    generated_at: str,
    policy: dict[str, Any],
    score_lineage: dict[str, Any],
) -> dict[str, Any]:
    """Build a bounded, explicitly unvalidated paper experiment hypothesis."""

    admission = experimental_pattern_admission(score, strategy, policy)
    reasons = admission["reasons"]
    if reasons:
        raise ValueError("pattern_not_experimental_hypothesis_eligible:" + ",".join(reasons))
    tier = str(admission["tier"])
    score_id = str(score["score_id"])
    strategy_id = str(score.get("strategy_family_id") or strategy["strategy_family_id"])
    instrument = str(score["instrument"])
    research_direction = str(score["direction_hypothesis"])
    direction = _normalise_experimental_direction(research_direction)
    if direction is None:
        raise ValueError("pattern_direction_not_explicitly_actionable")
    horizon = str(score.get("horizon_hypothesis") or "3d_forward")
    mapping = _instrument_mapping(score, strategy)
    pattern_relationship_id = stable_id(
        "experimental-pattern-relationship-v1",
        score_id,
        score.get("feature_vector_id"),
        instrument,
        direction,
        horizon,
    )
    research_goal_id = stable_id(
        "experimental-research-goal-v1",
        pattern_relationship_id,
        strategy_id,
    )
    identity_id = stable_id(
        "experimental-strategy-hypothesis-identity-v2",
        tier,
        research_goal_id,
        pattern_relationship_id,
        mapping.get("execution_proxy"),
        direction,
        horizon,
    )
    hypothesis_id = stable_id("experimental-strategy-hypothesis-v2", identity_id)
    eligible_source_rows = [
        row
        for row in score.get("feature_inputs", [])
        if isinstance(row, dict)
        and row.get("fresh") is True
        and row.get("source_key")
        and row.get("independence_cluster_id")
        and (
            (
                tier == BOUNDED_EXPERIMENTAL_TIER
                and row.get("quorum_eligible") is True
            )
            or (
                tier == DISCOVERY_MICRO_TIER
                and row.get("mapping_class") == "causal_strategy_mapping"
                and safe_float(row.get("trust_score"))
                >= safe_float(
                    policy.get("discovery_micro_admission", {}).get(
                        "minimum_catalyst_source_trust"
                    ),
                    0.70,
                )
            )
        )
    ]
    fresh_sources = [
        str(row.get("source_key"))
        for row in eligible_source_rows
    ]
    fresh_clusters = sorted(
        {
            str(row.get("independence_cluster_id"))
            for row in eligible_source_rows
        }
    )
    best = strategy.get("best_observed_rejected_result")
    best = best if isinstance(best, dict) else {}
    discovery_micro_net_expectancy = (
        safe_float(best.get("mean_net_return")) * 0.25
        if tier == DISCOVERY_MICRO_TIER and best.get("mean_net_return") is not None
        else None
    )
    source_packet_id = stable_id(
        "experimental-source-packet-v1",
        score_id,
        fresh_sources,
        score.get("input_fingerprint"),
    )
    invalidation_id = stable_id("experimental-invalidation-v1", identity_id)
    risk_concept_id = stable_id("experimental-risk-concept-v1", identity_id)
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_strategy_hypothesis_v3",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "hypothesis_id": hypothesis_id,
        "hypothesis_state": "ready_for_akber_review",
        "evidence_class": EXPERIMENTAL_UNVALIDATED,
        "experimental_tier": tier,
        "paper_experiment_purpose": (
            "Collect a real forward Alpaca Paper outcome without claiming a validated edge."
        ),
        "edge_lineage": {
            "edge_id": None,
            "promotion_class": None,
            "edge_claimed": False,
            "edge_registry_reference": score_lineage.get("edge_registry_reference", {}),
        },
        "pattern_lineage": {
            "pattern_relationship_id": pattern_relationship_id,
            "score_id": score_id,
            "operating_date": score.get("operating_date"),
            "feature_vector_id": score.get("feature_vector_id"),
            "input_fingerprint": score.get("input_fingerprint"),
            "score_model_version": score.get("model_version"),
            "raw_research_score": score.get("raw_pattern_score"),
            "score_is_probability": False,
            "score_is_validated_edge": False,
            "source_record_set_hash": score_lineage.get("pattern_score_record_set_hash"),
            "fresh_quorum_sources": fresh_sources,
            "fresh_independence_clusters": fresh_clusters,
            "fresh_catalyst_sources": fresh_sources,
            "source_confirmation_mode": (
                "two_independent_fresh_source_families"
                if tier == BOUNDED_EXPERIMENTAL_TIER
                else "one_fresh_causal_catalyst_plus_independent_live_market_confirmation"
            ),
            "independent_market_confirmation": {
                "current_market_price": score.get("features", {}).get(
                    "current_market_price"
                ),
                "volatility_context": score.get("features", {}).get(
                    "volatility_context"
                ),
                "volume_or_flow_context": score.get("features", {}).get(
                    "volume_or_flow_context"
                ),
                "provider_backed_runtime_confirmation_required_again_at_akber": True,
            },
            "complete": True,
        },
        "research_goal_lineage": {
            "research_goal_id": research_goal_id,
            "origin_edge_id": None,
            "origin_pattern_relationship_id": pattern_relationship_id,
            "origin_phase": "OR-5 current pattern scoring",
            "foundry_phase": PHASE_ID,
            "target_strategy_family": strategy_id,
            "evidence_chain": [
                "current provider-backed pattern score",
                "frozen historical strategy evidence map",
                "bounded experimental Strategy Foundry review",
                "Akber current-tradeability review required",
            ],
            "complete": True,
        },
        "candidate_identity_material": {
            "candidate_identity_id": identity_id,
            "identity_type": "experimental_research_hypothesis_identity_not_trade_candidate",
            "experimental_tier": tier,
            "research_goal_id": research_goal_id,
            "strategy_family_id": strategy_id,
            "origin_edge_id": None,
            "origin_pattern_relationship_id": pattern_relationship_id,
            "observed_instrument": instrument,
            "paperable_proxy_expression": mapping.get("execution_proxy"),
            "direction": direction,
            "research_direction_hypothesis": research_direction,
            "time_window": horizon,
            "signal_observation_date": score.get("operating_date"),
            "thesis": (
                f"Current evidence suggests {direction.replace('_', ' ')} for {instrument}; "
                "the paper experiment will test whether that relationship persists after costs."
            ),
            "source_packet_id": source_packet_id,
            "source_recipe_fingerprint": stable_id(
                "experimental-source-recipe-v1", strategy_id, fresh_sources, instrument
            ),
            "invalidation_id": invalidation_id,
            "risk_concept_id": risk_concept_id,
            "identity_fields": [
                "research_goal_id",
                "pattern_relationship_id",
                "instrument",
                "execution_proxy",
                "direction",
                "horizon",
            ],
            "not_trade_candidate": True,
            "not_idempotency_key_for_orders": True,
            "trade_candidate_created": False,
            "order_idempotency_key_created": False,
        },
        "strategy_mapping": {
            "strategy_family_id": strategy_id,
            "strategy_label": strategy.get("label") or strategy_id,
            "fit_score": score.get("features", {}).get("strategy_fit"),
            "fit_is_research_context_only": True,
            "emerging_strategy": bool(score.get("strategy_agnostic") is True),
        },
        "instrument_proxy_mapping": mapping,
        "direction_horizon": {
            "direction": direction,
            "research_direction_hypothesis": research_direction,
            "horizon": horizon,
            "regime": score.get("market_family"),
        },
        "catalyst_confirmation": {
            "catalyst": "fresh provider-backed source-price relationship",
            "fresh_quorum_sources": fresh_sources,
            "fresh_independence_clusters": fresh_clusters,
            "confirmation_mode": (
                "full_fresh_source_quorum"
                if tier == BOUNDED_EXPERIMENTAL_TIER
                else "fresh_catalyst_plus_independent_live_market_confirmation"
            ),
            "confirmation_required": [
                "current price and volatility context",
                "volume or flow confirmation",
                "liquidity and spread confirmation",
                "Akber pass",
            ],
            "confirmation_complete": False,
        },
        "entry_concept": {
            "summary": "Consider only the mapped paper proxy after current Akber, shadow, and risk gates pass.",
            "entry_authorized": False,
        },
        "invalidation_exit": {
            "invalidation_conditions": [
                (
                    "fresh source quorum falls below two independent families"
                    if tier == BOUNDED_EXPERIMENTAL_TIER
                    else "the fresh catalyst or independent market confirmation disappears"
                ),
                "current price confirmation reverses",
                "provisional return turns non-positive after expected costs",
            ],
            "exit_conditions": [
                "hypothesis horizon completes",
                "invalidation condition occurs",
                "risk or liquidity state deteriorates",
            ],
            "exit_order_created": False,
        },
        "risk_concept": {
            "maximum_loss_must_be_derived_from_invalidation": True,
            "liquidity_and_spread_required": True,
            "portfolio_correlation_required": True,
            "experimental_tier": tier,
            "experimental_risk_multiplier": (
                0.50 if tier == BOUNDED_EXPERIMENTAL_TIER else 0.10
            ),
            "absolute_notional_ceiling_usd": 5000.0,
            "expected_reward_to_risk": score.get("expected_reward_to_risk")
            or strategy.get("expected_reward_to_risk")
            or (1.50 if tier == DISCOVERY_MICRO_TIER else None),
            "discovery_micro_trade_design": (
                {
                    "volatility_scaled_invalidation": True,
                    "stop_distance_daily_volatility_multiple": 1.0,
                    "target_distance_stop_multiple": 1.50,
                    "minimum_reward_to_risk": 1.25,
                    "numeric_levels_must_be_built_from_fresh_provider_market_data": True,
                }
                if tier == DISCOVERY_MICRO_TIER
                else None
            ),
            "position_size": None,
            "risk_approval_created": False,
        },
        "expected_edge_range": {
            "gross_expectancy": best.get("mean_gross_return"),
            "net_expectancy": (
                score.get("provisional_current_net_expectancy_after_costs")
                if tier == DISCOVERY_MICRO_TIER
                and score.get("provisional_current_net_expectancy_after_costs") is not None
                else discovery_micro_net_expectancy
                if tier == DISCOVERY_MICRO_TIER
                else best.get("mean_net_return")
            ),
            "confidence_distribution": strategy.get("confidence_distribution"),
            "provisional_rejected_historical_result": True,
            "net_expectancy_source": (
                "shrunk_or_rejected_historical_signal_estimate_not_edge_proof"
                if tier == DISCOVERY_MICRO_TIER
                else "best_observed_rejected_historical_result"
            ),
            "positive_historical_expectancy_required_for_admission": (
                tier == BOUNDED_EXPERIMENTAL_TIER
            ),
            "positive_current_expectancy_required_before_router": True,
            "not_a_validated_expectancy": True,
            "range_is_research_estimate_only": True,
            "not_a_return_guarantee": True,
        },
        "known_failure_modes": strategy.get("failure_modes", [])
        or [
            "multiple-testing false discovery",
            "walk-forward instability",
            "current source regime differs from history",
            "fees, spread, or slippage erase the provisional return",
        ],
        "blocker_state": {
            "state": "akber_review_required",
            "blockers": ["akber_current_tradeability_review_required"],
            "router_eligible": False,
        },
        "paperability": {
            "state": "approved_proxy_available_review_required",
            "execution_proxy": mapping.get("execution_proxy"),
            "proxy_basis": mapping.get("proxy_basis"),
            "proxy_review_required": mapping.get("proxy_review_required"),
            "paper_route_required": "guarded_alpaca_paper_via_paperops",
            "paper_order_allowed": False,
        },
        "freshness": {
            "created_at": generated_at,
            "expires_at": _expiry(generated_at, horizon),
            "latest_supporting_sample": score.get("scoring_as_of"),
            "expiry_requires_new_evidence": True,
        },
        "qualitative_reasoning": {
            "summary": (
                "This is a bounded paper experiment formed from a current pattern. "
                + (
                    "It has positive but rejected historical evidence. "
                    if tier == BOUNDED_EXPERIMENTAL_TIER
                    else "Its small discovery tier is intended to collect forward evidence. "
                )
                + "It is not a validated edge."
            ),
            "cited_evidence_refs": [score_id, pattern_relationship_id, research_goal_id],
            "llm_numeric_proof_allowed": False,
            "llm_trade_authority": False,
        },
        "akber_review_allowed": True,
        "qualified_setup_created": False,
        "trade_candidate_created": False,
        "paper_order_created": False,
        "proof_credit_allowed": False,
        "authority": authority_flags(),
    }


def _rejection(
    *,
    generated_at: str,
    reasons: list[str],
    edge_id: str | None = None,
    score_id: str | None = None,
    strategy: dict[str, Any] | None = None,
    edge_registry_lineage: dict[str, Any] | None = None,
    rejection_scope: str = "edge_record",
) -> dict[str, Any]:
    strategy = strategy or {}
    strategy_id = str(strategy.get("strategy_family_id") or "") or None
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_strategy_hypothesis_rejection_v3",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "rejection_id": stable_id(
            "strategy-hypothesis-rejection-v3",
            rejection_scope,
            edge_id,
            score_id,
            strategy_id,
            reasons,
        ),
        "rejection_scope": rejection_scope,
        "edge_id": edge_id,
        "score_id": score_id,
        "strategy_family_id": strategy_id,
        "strategy_label": strategy.get("label"),
        "edge_registry_lineage": edge_registry_lineage or {},
        "rejection_reasons": reasons,
        "current_evidence_class": strategy.get("evidence_class"),
        "empirical_evidence": strategy.get("empirical_evidence", {}),
        "best_observed_rejected_result": strategy.get("best_observed_rejected_result"),
        "known_failure_modes": strategy.get("failure_modes", []),
        "permitted_next_action": strategy.get("next_evidence_requirement")
        or "repair or collect evidence, rerun OR-8, and re-enter OR-10",
        "configured_strategy_is_not_an_edge": rejection_scope == "strategy_family_evidence_gate",
        "exploratory_strategy_is_not_an_exploratory_edge": strategy.get("evidence_class")
        == "exploratory",
        "hypothesis_created": False,
        "trade_candidate_created": False,
        "qualified_setup_created": False,
        "risk_approval_created": False,
        "execution_approval_created": False,
        "paper_order_created": False,
        "broker_write_count": 0,
        "proof_credit_created": False,
        "authority": authority_flags(),
    }


def _strategy_gate_reasons(strategy: dict[str, Any]) -> list[str]:
    evidence_class = str(strategy.get("evidence_class") or "unknown")
    reasons = ["no_or10_admitted_edge_for_strategy"]
    if evidence_class == "exploratory":
        reasons.append("configured_strategy_exploratory_but_no_exploratory_edge_exists")
    elif evidence_class == "under_evidenced":
        reasons.append("strategy_under_evidenced")
    elif evidence_class == "degraded":
        reasons.append("strategy_evidence_degraded")
    elif evidence_class == "retired":
        reasons.append("strategy_retired")
    elif evidence_class != "evidence_backed":
        reasons.append("strategy_evidence_class_not_admissible")
    return reasons


def build_strategy_foundry_v3_from_inputs(
    edges: list[dict[str, Any]],
    edge_summary: dict[str, Any],
    strategy_map: dict[str, Any],
    *,
    generated_at: str,
    pattern_scores: list[dict[str, Any]] | None = None,
    experimental_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build validated hypotheses plus a separately bounded experimental lane."""

    generated = generated_at
    strategies = _strategy_by_id(strategy_map)
    input_lineage = _edge_registry_lineage(edges, edge_summary, strategy_map)
    input_errors = _foundry_input_errors(edges, edge_summary, strategy_map)
    experimental_enabled = pattern_scores is not None
    pattern_rows = pattern_scores or []
    policy = experimental_policy or {}
    if experimental_enabled:
        input_lineage.update(
            {
                "pattern_score_artifact": PATTERN_SCORES_ARTIFACT,
                "pattern_score_record_set_hash": record_set_hash(pattern_rows),
                "pattern_score_record_count": len(pattern_rows),
                "experimental_policy_artifact": EXPERIMENTAL_POLICY_ARTIFACT,
                "experimental_policy_version": policy.get("policy_version"),
            }
        )
    input_lineage["complete"] = not input_errors
    hypotheses: list[dict[str, Any]] = []
    rejections: list[dict[str, Any]] = []
    seen_identity_ids: set[str] = set()
    represented_strategy_ids: set[str] = set()

    if input_errors:
        rejections.append(
            _rejection(
                generated_at=generated,
                reasons=[f"invalid_or10_input:{error}" for error in input_errors],
                edge_registry_lineage=input_lineage,
                rejection_scope="or10_input_contract",
            )
        )
    else:
        for edge in edges:
            strategy_id, _fit = _best_strategy_id(edge)
            strategy = strategies.get(str(strategy_id)) if strategy_id else None
            if strategy_id:
                represented_strategy_ids.add(str(strategy_id))
            reasons = hypothesis_rejection_reasons(edge, strategy)
            if reasons:
                rejections.append(
                    _rejection(
                        generated_at=generated,
                        edge_id=str(edge.get("edge_id") or "") or None,
                        strategy=strategy,
                        edge_registry_lineage=input_lineage,
                        reasons=reasons,
                    )
                )
                continue
            hypothesis = build_strategy_hypothesis(
                edge,
                strategy or {},
                generated_at=generated,
                edge_registry_lineage=input_lineage,
            )
            identity_id = hypothesis["candidate_identity_material"]["candidate_identity_id"]
            if identity_id in seen_identity_ids:
                rejections.append(
                    _rejection(
                        generated_at=generated,
                        edge_id=str(edge.get("edge_id")),
                        strategy=strategy,
                        edge_registry_lineage=input_lineage,
                        reasons=["duplicate_hypothesis_identity"],
                    )
                )
                continue
            seen_identity_ids.add(identity_id)
            hypotheses.append(hypothesis)

        if experimental_enabled:
            score_lineage = {
                "pattern_score_record_set_hash": input_lineage.get(
                    "pattern_score_record_set_hash"
                ),
                "edge_registry_reference": input_lineage,
            }
            selected_score_ids, redundant_score_ids = _select_experimental_pattern_variants(
                pattern_rows,
                strategies,
                policy,
            )
            for score in pattern_rows:
                strategy_id = str(score.get("strategy_family_id") or "")
                strategy = strategies.get(strategy_id) if strategy_id else None
                reasons = experimental_pattern_rejection_reasons(score, strategy, policy)
                score_id = str(score.get("score_id") or "")
                if not reasons and score_id in redundant_score_ids:
                    reasons = ["redundant_instrument_variant_not_selected"]
                if not reasons and score_id not in selected_score_ids:
                    reasons = ["experimental_relationship_selection_missing"]
                if reasons:
                    rejections.append(
                        _rejection(
                            generated_at=generated,
                            score_id=score_id or None,
                            strategy=strategy,
                            edge_registry_lineage=input_lineage,
                            reasons=reasons,
                            rejection_scope="experimental_pattern_score_gate",
                        )
                    )
                    continue
                hypothesis = build_experimental_strategy_hypothesis(
                    score,
                    strategy or {},
                    generated_at=generated,
                    policy=policy,
                    score_lineage=score_lineage,
                )
                identity_id = hypothesis["candidate_identity_material"][
                    "candidate_identity_id"
                ]
                if identity_id in seen_identity_ids:
                    rejections.append(
                        _rejection(
                            generated_at=generated,
                            score_id=str(score.get("score_id") or "") or None,
                            strategy=strategy,
                            edge_registry_lineage=input_lineage,
                            reasons=["duplicate_hypothesis_identity"],
                            rejection_scope="experimental_pattern_score_gate",
                        )
                    )
                    continue
                seen_identity_ids.add(identity_id)
                represented_strategy_ids.add(strategy_id)
                hypotheses.append(hypothesis)

        for strategy_id in sorted(strategies):
            if strategy_id in represented_strategy_ids:
                continue
            strategy = strategies[strategy_id]
            rejections.append(
                _rejection(
                    generated_at=generated,
                    strategy=strategy,
                    edge_registry_lineage=input_lineage,
                    reasons=_strategy_gate_reasons(strategy),
                    rejection_scope="strategy_family_evidence_gate",
                )
            )

    state_counts = Counter(record["hypothesis_state"] for record in hypotheses)
    reason_counts = Counter(
        reason for record in rejections for reason in record.get("rejection_reasons", [])
    )
    edge_class_counts = Counter(str(edge.get("promotion_class")) for edge in edges)
    rejection_scope_counts = Counter(str(record.get("rejection_scope")) for record in rejections)
    valid_no_hypothesis_outcome = bool(not input_errors and not edges and not hypotheses)
    if input_errors:
        status = "foundry_blocked_invalid_or10_input"
    elif hypotheses:
        status = "foundry_complete_with_research_hypotheses"
    else:
        status = "foundry_complete_no_eligible_edges"
    primary = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_strategy_foundry_v3",
        "phase_id": PHASE_ID,
        "generated_at": generated,
        "status": status,
        "implementation_complete": not input_errors,
        "valid_no_hypothesis_outcome": valid_no_hypothesis_outcome,
        "input_validation_error_count": len(input_errors),
        "input_validation_errors": input_errors,
        "input_lineage": input_lineage,
        "admission_contract": (
            "durable_or10_edge_registry_plus_bounded_experimental_pattern_scores"
            if experimental_enabled
            else "durable_or10_edge_registry_only"
        ),
        "edge_registry_status": edge_summary.get("status"),
        "edge_count": len(edges),
        "eligible_edge_ids": sorted(
            str(edge.get("edge_id")) for edge in edges if edge.get("edge_id")
        ),
        "edge_class_counts": dict(sorted(edge_class_counts.items())),
        "strategy_family_count": len(strategies),
        "hypothesis_count": len(hypotheses),
        "hypothesis_state_counts": dict(sorted(state_counts.items())),
        "rejection_count": len(rejections),
        "rejection_reason_counts": dict(sorted(reason_counts.items())),
        "rejection_scope_counts": dict(sorted(rejection_scope_counts.items())),
        "akber_review_eligible_count": sum(
            record.get("akber_review_allowed") is True for record in hypotheses
        ),
        "exploratory_shadow_only_count": state_counts.get("shadow_only", 0),
        "experimental_hypothesis_count": sum(
            record.get("evidence_class") == EXPERIMENTAL_UNVALIDATED
            for record in hypotheses
        ),
        "bounded_experimental_hypothesis_count": sum(
            record.get("evidence_class") == EXPERIMENTAL_UNVALIDATED
            and record.get("experimental_tier") == BOUNDED_EXPERIMENTAL_TIER
            for record in hypotheses
        ),
        "discovery_micro_hypothesis_count": sum(
            record.get("evidence_class") == EXPERIMENTAL_UNVALIDATED
            and record.get("experimental_tier") == DISCOVERY_MICRO_TIER
            for record in hypotheses
        ),
        "validated_strategy_hypothesis_count": sum(
            record.get("evidence_class") == VALIDATED_PAPER_STRATEGY
            for record in hypotheses
        ),
        "candidate_created_count": 0,
        "qualified_setup_created_count": 0,
        "order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "paper_calendar_advanced": False,
        "pattern_score_rows_consumed_count": len(pattern_rows),
        "legacy_v2_hypotheses_consumed_count": 0,
        "authority": authority_flags(),
    }
    dashboard = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_strategy_foundry_v3_dashboard_summary",
        "generated_at": generated,
        "status": status,
        "headline": (
            "No empirical edge has reached strategy formation"
            if not hypotheses
            else f"{len(hypotheses)} governed research hypothesis{'es' if len(hypotheses) != 1 else ''} formed"
        ),
        "plain_english": (
            f"OR-10 reviewed {safe_int(edge_summary.get('backtest_result_count'))} empirical results "
            f"and admitted no edge. The foundry therefore created no trade-shaped idea; "
            f"{len(strategies)} strategy families remain at the evidence gate."
            if not hypotheses
            else "Validated-edge and experimental hypotheses remain visibly separate. Experimental ideas may collect forward paper evidence only after current Akber, risk, Router, and PaperOps gates pass."
        ),
        "edge_count": len(edges),
        "hypothesis_count": len(hypotheses),
        "experimental_hypothesis_count": primary["experimental_hypothesis_count"],
        "bounded_experimental_hypothesis_count": primary[
            "bounded_experimental_hypothesis_count"
        ],
        "discovery_micro_hypothesis_count": primary[
            "discovery_micro_hypothesis_count"
        ],
        "rejection_count": len(rejections),
        "strategy_family_gate_count": rejection_scope_counts.get(
            "strategy_family_evidence_gate", 0
        ),
        "akber_review_eligible_count": primary["akber_review_eligible_count"],
        "valid_no_hypothesis_outcome": valid_no_hypothesis_outcome,
        "evidence_gate": (
            "Validated hypotheses require an OR-10 edge. The standard experimental lane requires independent fresh-source quorum. The discovery lane may investigate one fresh causal catalyst only when independent live price, volatility, and volume evidence is also present; it remains capped at US$5,000, limited to one concurrent position, and unvalidated."
            if experimental_enabled
            else "Only a validated or explicitly exploratory OR-10 edge can enter Strategy Foundry V3."
        ),
        "closest_next_step": (
            "Improve or extend the provider-backed evidence, rerun the frozen OR-8 tests, and admit an edge through OR-10 only if it survives."
            if not hypotheses
            else "Assemble complete current-market evidence for Akber without treating the hypothesis as an approval."
        ),
        "paperops_state": "watch_only_research_lock_active",
        "research_only": True,
        "authority": authority_flags(),
    }
    return {
        "primary": primary,
        "hypotheses": hypotheses,
        "rejections": rejections,
        "dashboard": dashboard,
    }


def build_strategy_foundry_v3_state(
    settings: Settings | None = None,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    strategy_map = deepcopy(read_json(runtime / STRATEGY_MAP_ARTIFACT))
    pattern_scores = list(read_jsonl(runtime / PATTERN_SCORES_ARTIFACT))
    power_checks = read_json(runtime / POWER_MARKET_CHECK_ARTIFACT)
    if power_checks.get("safe_to_consume") is True:
        power_registry = read_json(runtime / POWER_MARKET_STRATEGY_ARTIFACT)
        power_strategies = power_registry.get("strategies")
        power_strategies = power_strategies if isinstance(power_strategies, list) else []
        existing = {
            str(row.get("strategy_family_id"))
            for row in strategy_map.get("strategies", [])
            if isinstance(row, dict) and row.get("strategy_family_id")
        }
        additions = [
            row
            for row in power_strategies
            if isinstance(row, dict)
            and row.get("strategy_family_id")
            and str(row.get("strategy_family_id")) not in existing
        ]
        strategy_map.setdefault("strategies", []).extend(additions)
        strategy_map["strategy_count"] = len(strategy_map.get("strategies", []))
        pattern_scores.extend(read_jsonl(runtime / POWER_MARKET_SCORES_ARTIFACT))
    return build_strategy_foundry_v3_from_inputs(
        read_jsonl(runtime / EDGE_REGISTRY_ARTIFACT),
        read_json(runtime / EDGE_SUMMARY_ARTIFACT),
        strategy_map,
        generated_at=generated_at or now_iso(),
        pattern_scores=pattern_scores,
        experimental_policy=read_json(runtime / EXPERIMENTAL_POLICY_ARTIFACT),
    )


def validate_strategy_foundry_v3_state(state: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    primary = state["primary"]
    hypotheses = state["hypotheses"]
    rejections = state["rejections"]
    identities: set[str] = set()
    hypothesis_ids: set[str] = set()
    eligible_edge_ids = set(primary.get("eligible_edge_ids", []))
    input_lineage = primary.get("input_lineage", {})
    if primary.get("input_validation_errors"):
        errors.extend(
            f"foundry_input_invalid:{error}" for error in primary.get("input_validation_errors", [])
        )
    admission_contract = primary.get("admission_contract")
    if admission_contract not in {
        "durable_or10_edge_registry_only",
        "durable_or10_edge_registry_plus_bounded_experimental_pattern_scores",
    }:
        errors.append("foundry_admission_contract_unknown")
    if input_lineage.get("complete") is not True:
        errors.append("foundry_or10_input_lineage_incomplete")
    if not input_lineage.get("edge_registry_record_set_hash"):
        errors.append("foundry_edge_registry_record_set_hash_missing")
    if not input_lineage.get("strategy_evidence_map_record_set_hash"):
        errors.append("foundry_strategy_map_record_set_hash_missing")
    for record in hypotheses:
        hypothesis_id = str(record.get("hypothesis_id") or "")
        if not hypothesis_id or hypothesis_id in hypothesis_ids:
            errors.append("hypothesis_id_missing_or_duplicate")
        hypothesis_ids.add(hypothesis_id)
        for field in REQUIRED_HYPOTHESIS_FIELDS:
            if not isinstance(record.get(field), dict) and field != "known_failure_modes":
                errors.append(f"hypothesis_required_field_missing:{hypothesis_id}:{field}")
            if field == "known_failure_modes" and not isinstance(record.get(field), list):
                errors.append(f"hypothesis_required_field_missing:{hypothesis_id}:{field}")
        evidence_class = record.get("evidence_class") or VALIDATED_PAPER_STRATEGY
        edge_lineage = record.get("edge_lineage", {})
        if evidence_class == EXPERIMENTAL_UNVALIDATED:
            tier = str(record.get("experimental_tier") or "")
            if tier not in {BOUNDED_EXPERIMENTAL_TIER, DISCOVERY_MICRO_TIER}:
                errors.append(f"experimental_hypothesis_tier_invalid:{hypothesis_id}")
            pattern_lineage = record.get("pattern_lineage", {})
            if edge_lineage.get("edge_id"):
                errors.append(f"experimental_hypothesis_claimed_edge:{hypothesis_id}")
            for field in ("pattern_relationship_id", "score_id", "source_record_set_hash"):
                if not pattern_lineage.get(field):
                    errors.append(
                        f"experimental_hypothesis_pattern_lineage_missing:{hypothesis_id}:{field}"
                    )
            if pattern_lineage.get("score_is_validated_edge") is not False:
                errors.append(f"experimental_hypothesis_claimed_validation:{hypothesis_id}")
            if not record.get("paper_experiment_purpose"):
                errors.append(f"experimental_hypothesis_purpose_missing:{hypothesis_id}")
            risk_concept = record.get("risk_concept", {})
            if tier == DISCOVERY_MICRO_TIER:
                if safe_float(risk_concept.get("absolute_notional_ceiling_usd")) != 5000.0:
                    errors.append(
                        f"discovery_micro_hypothesis_ceiling_invalid:{hypothesis_id}"
                    )
                if safe_float(risk_concept.get("experimental_risk_multiplier")) != 0.10:
                    errors.append(
                        f"discovery_micro_hypothesis_multiplier_invalid:{hypothesis_id}"
                    )
                if pattern_lineage.get("source_confirmation_mode") != (
                    "one_fresh_causal_catalyst_plus_independent_live_market_confirmation"
                ):
                    errors.append(
                        f"discovery_micro_hypothesis_confirmation_mode_invalid:{hypothesis_id}"
                    )
                market_confirmation = pattern_lineage.get(
                    "independent_market_confirmation", {}
                )
                if not isinstance(market_confirmation, dict) or any(
                    safe_float(market_confirmation.get(field)) < 1.0
                    for field in (
                        "current_market_price",
                        "volatility_context",
                        "volume_or_flow_context",
                    )
                ):
                    errors.append(
                        f"discovery_micro_hypothesis_market_confirmation_invalid:{hypothesis_id}"
                    )
        else:
            if not edge_lineage.get("edge_id"):
                errors.append(f"hypothesis_edge_lineage_missing:{hypothesis_id}")
            elif edge_lineage.get("edge_id") not in eligible_edge_ids:
                errors.append(f"hypothesis_edge_not_in_or10_registry:{hypothesis_id}")
            registry_reference = edge_lineage.get("edge_registry_reference", {})
            if registry_reference.get("complete") is not True or registry_reference.get(
                "edge_registry_record_set_hash"
            ) != input_lineage.get("edge_registry_record_set_hash"):
                errors.append(f"hypothesis_edge_registry_reference_invalid:{hypothesis_id}")
        goal = record.get("research_goal_lineage", {})
        if not goal.get("research_goal_id") or goal.get("complete") is not True:
            errors.append(f"hypothesis_research_goal_lineage_incomplete:{hypothesis_id}")
        identity_material = record.get("candidate_identity_material", {})
        identity = identity_material.get("candidate_identity_id")
        if not identity or identity in identities:
            errors.append(f"hypothesis_identity_missing_or_duplicate:{hypothesis_id}")
        identities.add(str(identity))
        for field in (
            "source_packet_id",
            "source_recipe_fingerprint",
            "invalidation_id",
            "risk_concept_id",
            "thesis",
        ):
            if not identity_material.get(field):
                errors.append(f"hypothesis_identity_material_incomplete:{hypothesis_id}:{field}")
        if (
            identity_material.get("not_trade_candidate") is not True
            or identity_material.get("not_idempotency_key_for_orders") is not True
        ):
            errors.append(f"hypothesis_identity_boundary_missing:{hypothesis_id}")
        state_name = record.get("hypothesis_state")
        if state_name not in ALLOWED_HYPOTHESIS_STATES:
            errors.append(f"hypothesis_state_invalid:{hypothesis_id}")
        if (
            edge_lineage.get("promotion_class") == "exploratory_research_edge"
            and state_name != "shadow_only"
        ):
            errors.append(f"exploratory_hypothesis_not_shadow_only:{hypothesis_id}")
        if (
            edge_lineage.get("promotion_class") == "exploratory_research_edge"
            and record.get("akber_review_allowed") is not False
        ):
            errors.append(f"exploratory_hypothesis_akber_enabled:{hypothesis_id}")
        created = parse_timestamp(record.get("freshness", {}).get("created_at"))
        expires = parse_timestamp(record.get("freshness", {}).get("expires_at"))
        if created is None or expires is None or expires <= created:
            errors.append(f"hypothesis_expiry_invalid:{hypothesis_id}")
        if any(
            record.get(field) is not False
            for field in (
                "qualified_setup_created",
                "trade_candidate_created",
                "paper_order_created",
                "proof_credit_allowed",
            )
        ):
            errors.append(f"hypothesis_created_authority_object:{hypothesis_id}")
        qualitative = record.get("qualitative_reasoning", {})
        if (
            qualitative.get("llm_numeric_proof_allowed") is not False
            or qualitative.get("llm_trade_authority") is not False
            or not qualitative.get("cited_evidence_refs")
        ):
            errors.append(f"hypothesis_llm_boundary_invalid:{hypothesis_id}")
        errors.extend(validate_authority(record.get("authority", {}), prefix="foundry_hypothesis"))
    rejection_ids: set[str] = set()
    for record in rejections:
        rejection_id = str(record.get("rejection_id") or "")
        if not rejection_id or rejection_id in rejection_ids:
            errors.append("foundry_rejection_id_missing_or_duplicate")
        rejection_ids.add(rejection_id)
        if not record.get("rejection_reasons"):
            errors.append("foundry_rejection_reason_missing")
        if record.get("hypothesis_created") is not False:
            errors.append("foundry_rejection_created_hypothesis")
        if record.get("rejection_scope") == "strategy_family_evidence_gate" and not record.get(
            "strategy_family_id"
        ):
            errors.append("foundry_strategy_gate_missing_strategy_family")
        if any(
            record.get(field) not in (False, 0)
            for field in (
                "trade_candidate_created",
                "qualified_setup_created",
                "risk_approval_created",
                "execution_approval_created",
                "paper_order_created",
                "broker_write_count",
                "proof_credit_created",
            )
        ):
            errors.append(f"foundry_rejection_created_authority_object:{rejection_id}")
        errors.extend(validate_authority(record.get("authority", {}), prefix="foundry_rejection"))
    if primary.get("edge_count") == 0 and any(
        record.get("evidence_class") != EXPERIMENTAL_UNVALIDATED
        for record in hypotheses
    ):
        errors.append("foundry_created_nonexperimental_hypothesis_without_edge")
    if primary.get("hypothesis_count") != len(hypotheses):
        errors.append("foundry_hypothesis_count_mismatch")
    if primary.get("rejection_count") != len(rejections):
        errors.append("foundry_rejection_count_mismatch")
    if primary.get("edge_count") != len(eligible_edge_ids):
        errors.append("foundry_eligible_edge_id_count_mismatch")
    if (
        primary.get("edge_count") == 0
        and primary.get("input_validation_error_count") == 0
        and primary.get("hypothesis_count") == 0
        and primary.get("valid_no_hypothesis_outcome") is not True
    ):
        errors.append("foundry_valid_no_hypothesis_outcome_missing")
    if (
        primary.get("edge_count") == 0
        and primary.get("input_validation_error_count") == 0
        and primary.get("hypothesis_count") == 0
        and primary.get("rejection_scope_counts", {}).get("strategy_family_evidence_gate")
        != primary.get("strategy_family_count")
    ):
        errors.append("foundry_strategy_gate_coverage_incomplete")
    if (
        admission_contract == "durable_or10_edge_registry_only"
        and primary.get("pattern_score_rows_consumed_count") != 0
    ):
        errors.append("foundry_consumed_pattern_scores_outside_experimental_contract")
    if primary.get("legacy_v2_hypotheses_consumed_count") != 0:
        errors.append("foundry_consumed_legacy_v2_hypotheses")
    for field in (
        "candidate_created_count",
        "qualified_setup_created_count",
        "order_created_count",
        "broker_write_count",
        "proof_credit_created_count",
    ):
        if primary.get(field) != 0:
            errors.append(f"foundry_authority_count_nonzero:{field}")
    if primary.get("paper_calendar_advanced") is not False:
        errors.append("foundry_advanced_paper_calendar")
    errors.extend(validate_authority(primary.get("authority", {}), prefix="foundry_primary"))
    errors.extend(
        validate_authority(state["dashboard"].get("authority", {}), prefix="foundry_dashboard")
    )
    return unique_errors(errors)


def build_and_write_strategy_foundry_v3(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    store = AtomicArtifactStore(runtime)
    state = build_strategy_foundry_v3_state(settings)
    store.write_json(PRIMARY_ARTIFACT, state["primary"])
    store.write_jsonl(HYPOTHESES_ARTIFACT, state["hypotheses"])
    store.write_jsonl(REJECTIONS_ARTIFACT, state["rejections"])
    store.write_json(DASHBOARD_ARTIFACT, state["dashboard"])
    errors = validate_strategy_foundry_v3_state(state)
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_strategy_foundry_v3_checks",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "implementation_ready": not errors,
        "implementation_complete": state["primary"]["implementation_complete"],
        "valid_no_hypothesis_outcome": state["primary"]["valid_no_hypothesis_outcome"],
        "admission_contract": state["primary"]["admission_contract"],
        "input_lineage": state["primary"]["input_lineage"],
        "input_validation_error_count": state["primary"]["input_validation_error_count"],
        "edge_count": state["primary"]["edge_count"],
        "strategy_family_count": state["primary"]["strategy_family_count"],
        "hypothesis_count": state["primary"]["hypothesis_count"],
        "rejection_count": state["primary"]["rejection_count"],
        "rejection_scope_counts": state["primary"]["rejection_scope_counts"],
        "akber_review_eligible_count": state["primary"]["akber_review_eligible_count"],
        "exploratory_shadow_only_count": state["primary"]["exploratory_shadow_only_count"],
        "pattern_score_rows_consumed_count": state["primary"][
            "pattern_score_rows_consumed_count"
        ],
        "experimental_hypothesis_count": state["primary"][
            "experimental_hypothesis_count"
        ],
        "bounded_experimental_hypothesis_count": state["primary"][
            "bounded_experimental_hypothesis_count"
        ],
        "discovery_micro_hypothesis_count": state["primary"][
            "discovery_micro_hypothesis_count"
        ],
        "legacy_v2_hypotheses_consumed_count": 0,
        "candidate_created_count": 0,
        "qualified_setup_created_count": 0,
        "order_created_count": 0,
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "paper_calendar_advanced": False,
        "paperops_watch_only": True,
        "authority": authority_flags(),
    }
    store.write_json(CHECK_ARTIFACT, checks)
    return state, checks, errors
