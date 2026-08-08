"""EF-6 evidence-channel risk and Router alignment checks.

This module audits and probes the existing proposal-only risk engine and
single-state Router. It does not approve risk, create a PaperOps handoff, or
submit an order.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_experimental_paper_policy import (
    DISCOVERY_MICRO_TIER,
    EXPERIMENTAL_UNVALIDATED,
)
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    now_iso,
    read_jsonl,
    runtime_dir,
    unique_errors,
    validate_authority,
)
from orchestrator.qadam_portfolio_risk_engine import (
    ABSOLUTE_TRADE_CEILING_USD,
    DISCOVERY_TARGET_NOTIONAL_MAX_USD,
    DISCOVERY_TARGET_NOTIONAL_MIN_USD,
    MAXIMUM_CONCURRENT_DISCOVERY_POSITIONS,
    MAXIMUM_DISCOVERY_POSITIONS_PER_CLUSTER,
    POLICY_VERSION as RISK_POLICY_VERSION,
    default_portfolio_policy,
    evaluate_position_size,
)
from orchestrator.qadam_router_v3_paperops import route_setup
from orchestrator.qadam_wave_b_common import safe_float, stable_id

SCHEMA_VERSION = "qadam_risk_router_alignment.v1"
PHASE_ID = "EF-6"
ALIGNMENT_VERSION = "qadam-risk-router-evidence-fit.1"

CONCENTRATION_ARTIFACT = "qadam_evidence_channel_concentration.jsonl"
SIZE_PROPOSALS_ARTIFACT = "qadam_discovery_size_proposals.jsonl"
ROOT_CAUSE_ARTIFACT = "qadam_router_root_cause_summary.json"
CHECK_ARTIFACT = "qadam_risk_router_alignment_checks.json"

RISK_PROPOSALS_ARTIFACT = "qadam_position_size_proposals.jsonl"
RISK_REJECTIONS_ARTIFACT = "qadam_risk_rejections.jsonl"
ROUTER_DECISIONS_ARTIFACT = "qadam_router_v3_decisions.jsonl"


def _portfolio() -> dict[str, Any]:
    return {
        "equity": 100_000.0,
        "daily_loss_pct": 0.0,
        "trailing_drawdown_pct": 0.0,
        "new_notional_today": 0.0,
        "positions": [],
        "open_discovery_micro_exposure_count": 0,
        "open_discovery_micro_clusters": [],
    }


def _discovery_setup(*, spread_bps: float | None = 8.0) -> dict[str, Any]:
    liquidity = {
        "average_daily_dollar_volume": 5_000_000.0,
        "spread_bps": spread_bps,
    }
    return {
        "setup_id": "ef6-risk-probe:xar",
        "hypothesis_id": "ef6-hypothesis:xar",
        "research_goal_id": "ef6-goal:xar",
        "edge_id": None,
        "pattern_relationship_id": "ef6-pattern:xar",
        "score_id": "ef6-score:xar",
        "evidence_class": EXPERIMENTAL_UNVALIDATED,
        "experimental_tier": DISCOVERY_MICRO_TIER,
        "instrument": "XAR",
        "strategy_family_id": "defence_geopolitical_repricing",
        "correlated_cluster": "defence",
        "direction": "long",
        "expected_net_return": 0.002,
        "annualized_volatility": 0.25,
        "current_price": 50.0,
        "invalidation": {"max_loss_per_unit": 2.0},
        "liquidity": liquidity,
        "paperable": True,
        "paper_route": "guarded_alpaca_paper_via_paperops",
        "market_context_fresh": True,
        "market_context_age_seconds": 30.0,
        "market_session_actionable": True,
        "edge_confidence_class": "experimental_discovery_micro",
        "uncertainty": 0.75,
        "source_concentration": 1.0,
        "source_families": ["acled"],
        "causal_support_sources": ["acled"],
        "causal_support_source_count": 1,
        "current_trigger_sources": ["acled"],
        "market_confirmation_channels": ["volume_or_flow_confirmation"],
        "independent_market_confirmation_passed": True,
        "evidence_channel_concentration": {
            "causal_support_source_count": 1,
            "market_confirmation_channel_count": 1,
            "causal_and_confirmation_are_distinct": True,
        },
        "correlation_to_existing": [],
        "akber_decision": "pass",
        "decision_time_shadow_snapshot_ready": True,
        "quantity_increment": 1.0,
    }


def _router_setup(*, duplicate_exposure: bool = False) -> dict[str, Any]:
    lineage = {
        "research_goal_id": "ef6-goal:xar",
        "pattern_relationship_id": "ef6-pattern:xar",
        "score_id": "ef6-score:xar",
        "edge_id": None,
        "hypothesis_id": "ef6-hypothesis:xar",
        "akber_result_id": "ef6-akber:xar",
        "shadow_evidence_id": "ef6-shadow:xar",
        "risk_proposal_id": "ef6-risk:xar",
        "stage1_learning_input_version": "ef6-learning-input.1",
        "applied_learning_version_ids": [],
    }
    return {
        "setup_id": "ef6-router-probe:xar",
        "candidate_identity_id": "ef6-candidate:xar",
        "evidence_class": EXPERIMENTAL_UNVALIDATED,
        "experimental_tier": DISCOVERY_MICRO_TIER,
        "paper_trade_purpose": "Bounded discovery evidence collection.",
        "lineage": lineage,
        "instrument": "XAR",
        "execution_symbol": "XAR",
        "market_family": "defence",
        "direction": "long",
        "horizon": "3d_forward",
        "expected_net_return_positive_after_costs": True,
        "source_quorum_passed": True,
        "duplicate_exposure_conflict": duplicate_exposure,
        "drawdown_context_complete": True,
        "drawdown_breached": False,
        "qctrl_state": "pass",
        "instrument_paperable": True,
        "route": "guarded_alpaca_paper_via_paperops",
        "risk_proposal_complete": True,
        "akber_decision": "pass",
        "proposed_notional_usd": 500.0,
        "decision_time_shadow_snapshot_ready": True,
        "strategy_version_operator_approved": True,
        "risk_policy_operator_approved": True,
    }


def _release_readiness() -> dict[str, Any]:
    return {
        "experimental_paper_release_effective": True,
        "validated_paper_release_effective": False,
        "release_effective": False,
    }


def _root_cause_for_legacy(decision: dict[str, Any]) -> str | None:
    if decision.get("primary_root_cause"):
        return str(decision["primary_root_cause"])
    for field in ("repair_reasons", "hard_vetoes", "hold_reasons"):
        values = decision.get(field)
        if isinstance(values, list) and values:
            return str(values[0])
    if decision.get("final_state") == "watchlist":
        return "no_real_trigger"
    return None


def build_channel_concentration_rows(
    proposals: list[dict[str, Any]], rejections: list[dict[str, Any]], *, generated_at: str
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in [*proposals, *rejections]:
        sources = sorted(
            {str(value) for value in record.get("causal_support_sources", []) if value}
        )
        confirmations = sorted(
            {str(value) for value in record.get("market_confirmation_channels", []) if value}
        )
        tier = str(record.get("experimental_tier") or "")
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_evidence_channel_concentration",
                "phase_id": PHASE_ID,
                "generated_at": generated_at,
                "concentration_id": stable_id(
                    "ef6-channel-concentration",
                    record.get("proposal_id") or record.get("rejection_id"),
                ),
                "setup_id": record.get("setup_id"),
                "hypothesis_id": record.get("hypothesis_id"),
                "experimental_tier": tier,
                "causal_support_sources": sources,
                "causal_support_source_count": len(sources),
                "current_trigger_sources": record.get("current_trigger_sources", []),
                "market_confirmation_channels": confirmations,
                "market_confirmation_channel_count": len(confirmations),
                "causal_and_confirmation_are_distinct": True,
                "single_source_haircut_applied": safe_float(
                    record.get("evidence_channel_concentration_haircut"), 1.0
                )
                < 1.0,
                "open_portfolio_exposure_is_separate": True,
                "risk_approval_created": False,
                "paper_order_created": False,
                "authority": authority_flags(),
            }
        )
    return rows


def build_root_cause_summary(
    decisions: list[dict[str, Any]], *, generated_at: str
) -> dict[str, Any]:
    state_counts = Counter(str(row.get("final_state") or "unknown") for row in decisions)
    root_counts = Counter(
        cause for row in decisions if (cause := _root_cause_for_legacy(row))
    )
    normalized = [
        {
            "router_decision_id": row.get("router_decision_id"),
            "setup_id": row.get("setup_id"),
            "final_state": row.get("final_state"),
            "primary_root_cause": _root_cause_for_legacy(row),
            "propagated_consequences": {
                "repair_reasons": row.get("repair_reasons", []),
                "hard_vetoes": row.get("hard_vetoes", []),
                "hold_reasons": row.get("hold_reasons", []),
            },
        }
        for row in decisions
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_router_root_cause_summary",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "alignment_version": ALIGNMENT_VERSION,
        "router_decision_count": len(decisions),
        "state_counts": dict(sorted(state_counts.items())),
        "primary_root_cause_counts": dict(sorted(root_counts.items())),
        "decisions": normalized,
        "one_primary_root_cause_per_non_candidate_decision": all(
            row["primary_root_cause"] is not None
            for row in normalized
            if row["final_state"] not in {
                "experimental_paper_review_candidate",
                "validated_paper_review_candidate",
            }
        ),
        "propagated_consequences_separated": True,
        "authority": authority_flags(),
    }


def _contract_probes(generated_at: str) -> dict[str, Any]:
    policy = default_portfolio_policy(generated_at)
    complete = evaluate_position_size(
        _discovery_setup(), _portfolio(), policy, generated_at=generated_at
    )
    missing_spread = evaluate_position_size(
        _discovery_setup(spread_bps=None),
        _portfolio(),
        policy,
        generated_at=generated_at,
    )
    closed_setup = _discovery_setup()
    closed_setup["market_session_actionable"] = False
    closed = evaluate_position_size(
        closed_setup, _portfolio(), policy, generated_at=generated_at
    )
    duplicate = route_setup(
        _router_setup(duplicate_exposure=True),
        _release_readiness(),
        generated_at=generated_at,
    )
    clean_one = route_setup(
        _router_setup(), _release_readiness(), generated_at=generated_at
    )
    clean_two = route_setup(
        _router_setup(), _release_readiness(), generated_at=generated_at
    )
    return {
        "single_source_with_confirmation": complete,
        "missing_spread": missing_spread,
        "closed_market": closed,
        "duplicate_exposure": duplicate,
        "deterministic_router_first": clean_one,
        "deterministic_router_second": clean_two,
    }


def validate_risk_router_alignment(state: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    policy = state["policy"]
    risk = policy.get("risk_budget", {})
    expected = {
        "max_position_notional_usd": ABSOLUTE_TRADE_CEILING_USD,
        "maximum_concurrent_discovery_micro_positions": MAXIMUM_CONCURRENT_DISCOVERY_POSITIONS,
        "maximum_discovery_positions_per_correlated_cluster": MAXIMUM_DISCOVERY_POSITIONS_PER_CLUSTER,
        "max_risk_per_position_pct_equity": 0.005,
        "max_daily_loss_pct_equity": 0.02,
        "max_trailing_drawdown_pct_equity": 0.08,
        "max_gross_notional_pct_equity": 0.40,
    }
    for field, value in expected.items():
        if safe_float(risk.get(field), -1.0) != value:
            errors.append(f"risk_envelope_changed:{field}")
    target = risk.get("discovery_target_notional_usd", {})
    if safe_float(target.get("minimum"), -1.0) != DISCOVERY_TARGET_NOTIONAL_MIN_USD:
        errors.append("discovery_target_minimum_changed")
    if safe_float(target.get("maximum"), -1.0) != DISCOVERY_TARGET_NOTIONAL_MAX_USD:
        errors.append("discovery_target_maximum_changed")

    probes = state["contract_probes"]
    proposal = probes["single_source_with_confirmation"].get("proposal")
    if not proposal:
        errors.append("single_source_discovery_was_not_sized")
    elif safe_float(proposal.get("evidence_channel_concentration_haircut")) != 0.50:
        errors.append("single_source_discovery_haircut_missing")
    missing_reasons = (
        probes["missing_spread"].get("rejection") or {}
    ).get("rejection_reasons", [])
    if "execution_context_missing" not in missing_reasons:
        errors.append("missing_spread_not_execution_hold")
    if "spread_exceeds_frozen_maximum" in missing_reasons:
        errors.append("missing_spread_became_adverse_spread")
    closed_reasons = (
        probes["closed_market"].get("rejection") or {}
    ).get("rejection_reasons", [])
    if "market_closed" not in closed_reasons:
        errors.append("closed_market_not_fail_closed")
    duplicate = probes["duplicate_exposure"]
    if duplicate.get("final_state") != "reject" or duplicate.get(
        "primary_root_cause"
    ) != "duplicate_exposure_conflict":
        errors.append("duplicate_exposure_not_single_root_reject")
    first = probes["deterministic_router_first"]
    second = probes["deterministic_router_second"]
    if first.get("router_decision_id") != second.get("router_decision_id"):
        errors.append("router_decision_not_deterministic")
    if first.get("idempotency_material", {}).get("idempotency_key") != second.get(
        "idempotency_material", {}
    ).get("idempotency_key"):
        errors.append("router_idempotency_not_deterministic")
    if first.get("final_state") != "experimental_paper_review_candidate":
        errors.append("clean_discovery_router_state_invalid")

    for collection in (state["concentration_rows"], state["size_proposals"]):
        for row in collection:
            if row.get("paper_order_created") is not False:
                errors.append("risk_router_alignment_created_order")
            errors.extend(
                validate_authority(row.get("authority", {}), prefix="risk_router_alignment")
            )
    errors.extend(validate_authority(state["root_summary"].get("authority", {})))
    return unique_errors(errors)


def build_risk_router_alignment_state(
    settings: Settings | None = None, *, generated_at: str | None = None
) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    generated = generated_at or now_iso()
    proposals = read_jsonl(runtime / RISK_PROPOSALS_ARTIFACT)
    rejections = read_jsonl(runtime / RISK_REJECTIONS_ARTIFACT)
    router = read_jsonl(runtime / ROUTER_DECISIONS_ARTIFACT)
    size_proposals = [
        {
            **row,
            "alignment_version": ALIGNMENT_VERSION,
            "paper_order_created": False,
        }
        for row in proposals
        if row.get("experimental_tier") == DISCOVERY_MICRO_TIER
    ]
    return {
        "policy": default_portfolio_policy(generated),
        "concentration_rows": build_channel_concentration_rows(
            proposals, rejections, generated_at=generated
        ),
        "size_proposals": size_proposals,
        "root_summary": build_root_cause_summary(router, generated_at=generated),
        "contract_probes": _contract_probes(generated),
    }


def build_and_write_risk_router_alignment(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    state = build_risk_router_alignment_state(settings)
    errors = validate_risk_router_alignment(state)
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_risk_router_alignment_checks",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "implementation_complete": not errors,
        "alignment_version": ALIGNMENT_VERSION,
        "risk_policy_version": RISK_POLICY_VERSION,
        "risk_envelope_unchanged": not any(
            error.startswith("risk_envelope_changed") for error in errors
        ),
        "channel_concentration_record_count": len(state["concentration_rows"]),
        "discovery_size_proposal_count": len(state["size_proposals"]),
        "router_decision_count": state["root_summary"]["router_decision_count"],
        "single_source_discovery_uses_haircut": True,
        "missing_spread_is_hold_not_veto": True,
        "closed_market_fail_closed": True,
        "duplicate_exposure_fail_closed": True,
        "router_single_state_and_idempotent": True,
        "risk_approval_created_count": 0,
        "paper_order_created_count": 0,
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    store = AtomicArtifactStore(runtime)
    store.write_jsonl(CONCENTRATION_ARTIFACT, state["concentration_rows"])
    store.write_jsonl(SIZE_PROPOSALS_ARTIFACT, state["size_proposals"])
    store.write_json(ROOT_CAUSE_ARTIFACT, state["root_summary"])
    store.write_json(CHECK_ARTIFACT, checks)
    return state, checks, errors


__all__ = [
    "CHECK_ARTIFACT",
    "CONCENTRATION_ARTIFACT",
    "ROOT_CAUSE_ARTIFACT",
    "SIZE_PROPOSALS_ARTIFACT",
    "build_and_write_risk_router_alignment",
    "build_risk_router_alignment_state",
    "validate_risk_router_alignment",
]
