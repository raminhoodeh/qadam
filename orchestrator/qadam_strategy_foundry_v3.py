"""OR-11 Strategy Foundry V3.

Only durable OR-10 edge records may become V3 strategy hypotheses. The
resulting records are research objects for Akber review, never trade
candidates, qualified setups, approvals, or orders.
"""

from __future__ import annotations

from collections import Counter
from datetime import timedelta
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
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
    proxy = instrument if instrument in paperable else (paperable[0] if paperable else None)
    return {
        "observed_instrument": instrument,
        "execution_proxy": proxy,
        "observed_instrument_directly_paperable": instrument in paperable,
        "paperable_proxy_symbols": paperable,
        "proxy_basis": "direct" if instrument in paperable else "strategy_family_proxy",
        "proxy_review_required": proxy is not None and proxy != instrument,
        "paper_order_allowed": False,
    }


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


def _rejection(
    *,
    generated_at: str,
    reasons: list[str],
    edge_id: str | None = None,
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
            strategy_id,
            reasons,
        ),
        "rejection_scope": rejection_scope,
        "edge_id": edge_id,
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
) -> dict[str, Any]:
    """Build OR-11 strictly from the durable OR-10 output contract."""

    generated = generated_at
    strategies = _strategy_by_id(strategy_map)
    input_lineage = _edge_registry_lineage(edges, edge_summary, strategy_map)
    input_errors = _foundry_input_errors(edges, edge_summary, strategy_map)
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
        "admission_contract": "durable_or10_edge_registry_only",
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
        "candidate_created_count": 0,
        "qualified_setup_created_count": 0,
        "order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "paper_calendar_advanced": False,
        "pattern_score_rows_consumed_count": 0,
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
            else f"{len(hypotheses)} edge-backed research hypothesis{'es' if len(hypotheses) != 1 else ''} formed"
        ),
        "plain_english": (
            f"OR-10 reviewed {safe_int(edge_summary.get('backtest_result_count'))} empirical results "
            f"and admitted no edge. The foundry therefore created no trade-shaped idea; "
            f"{len(strategies)} strategy families remain at the evidence gate."
            if not hypotheses
            else "Each idea is tied to an admitted OR-10 edge. Validated-edge ideas may proceed to Akber review; exploratory-edge ideas remain shadow-only."
        ),
        "edge_count": len(edges),
        "hypothesis_count": len(hypotheses),
        "rejection_count": len(rejections),
        "strategy_family_gate_count": rejection_scope_counts.get(
            "strategy_family_evidence_gate", 0
        ),
        "akber_review_eligible_count": primary["akber_review_eligible_count"],
        "valid_no_hypothesis_outcome": valid_no_hypothesis_outcome,
        "evidence_gate": "Only a validated or explicitly exploratory OR-10 edge can enter Strategy Foundry V3.",
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
    return build_strategy_foundry_v3_from_inputs(
        read_jsonl(runtime / EDGE_REGISTRY_ARTIFACT),
        read_json(runtime / EDGE_SUMMARY_ARTIFACT),
        read_json(runtime / STRATEGY_MAP_ARTIFACT),
        generated_at=generated_at or now_iso(),
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
    if primary.get("admission_contract") != "durable_or10_edge_registry_only":
        errors.append("foundry_admission_contract_not_edge_registry_only")
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
        edge_lineage = record.get("edge_lineage", {})
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
    if primary.get("edge_count") == 0 and hypotheses:
        errors.append("foundry_created_hypothesis_without_edge")
    if primary.get("hypothesis_count") != len(hypotheses):
        errors.append("foundry_hypothesis_count_mismatch")
    if primary.get("rejection_count") != len(rejections):
        errors.append("foundry_rejection_count_mismatch")
    if primary.get("edge_count") != len(eligible_edge_ids):
        errors.append("foundry_eligible_edge_id_count_mismatch")
    if (
        primary.get("edge_count") == 0
        and primary.get("input_validation_error_count") == 0
        and primary.get("valid_no_hypothesis_outcome") is not True
    ):
        errors.append("foundry_valid_no_hypothesis_outcome_missing")
    if (
        primary.get("edge_count") == 0
        and primary.get("input_validation_error_count") == 0
        and primary.get("rejection_scope_counts", {}).get("strategy_family_evidence_gate")
        != primary.get("strategy_family_count")
    ):
        errors.append("foundry_strategy_gate_coverage_incomplete")
    if primary.get("pattern_score_rows_consumed_count") != 0:
        errors.append("foundry_consumed_legacy_pattern_scores")
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
        "pattern_score_rows_consumed_count": 0,
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
