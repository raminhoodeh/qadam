"""Evidence-fit conversion helpers for bounded discovery-paper experiments.

This module is deliberately narrower than an edge validator. It translates a
current, provider-backed setup into a conservative decision-time expectancy and
records what is still missing. A positive result is permission to continue to
Akber review at discovery-micro size, not proof of alpha or order authority.
"""

from __future__ import annotations

from math import sqrt
import re
from typing import Any

from orchestrator.qadam_operator_ready_common import authority_flags
from orchestrator.qadam_wave_b_common import safe_float, stable_id

SCHEMA_VERSION = "qadam_discovery_micro_conversion.v1"

CURRENT_EXPECTANCY_ARTIFACT = "qadam_current_expectancy_v2.jsonl"
DIRECTION_RETRY_ARTIFACT = "qadam_direction_retry_queue.jsonl"
CALIBRATION_ARTIFACT = "qadam_discovery_micro_calibration.json"
CERTIFICATION_ARTIFACT = "qadam_discovery_micro_conversion_certification.json"

ACTIONABLE_DIRECTIONS = {"long", "short"}

EVENT_FAMILIES = {
    "crude_oil_energy_security_disruption",
    "defence_repricing_geopolitical_watch",
    "semiconductor_policy_options_asymmetry",
}
REGIME_FAMILIES = {"silver_macro_liquidity_stress", "power_scarcity_congestion"}
PREDICTION_FAMILY = "prediction_market_geopolitical_dislocation"

INSTRUMENT_ROLES: dict[str, dict[str, str]] = {
    "CL=F": {"role": "futures_context", "basis_risk": "none_research_context"},
    "SI=F": {"role": "futures_context", "basis_risk": "none_research_context"},
    "USO": {"role": "oil_execution_proxy", "basis_risk": "futures_roll_and_etf_basis"},
    "BNO": {"role": "brent_execution_proxy", "basis_risk": "futures_roll_and_etf_basis"},
    "XLE": {"role": "energy_equity_proxy", "basis_risk": "equity_beta_and_company_mix"},
    "ITA": {"role": "defence_sector_proxy", "basis_risk": "sector_basket_mix"},
    "XAR": {"role": "defence_sector_proxy", "basis_risk": "sector_basket_mix"},
    "PPA": {"role": "aerospace_defence_proxy", "basis_risk": "sector_basket_mix"},
    "LMT": {"role": "defence_single_name", "basis_risk": "company_specific_risk"},
    "RTX": {"role": "defence_single_name", "basis_risk": "company_specific_risk"},
    "SMH": {"role": "semiconductor_sector_proxy", "basis_risk": "sector_basket_mix"},
    "SOXX": {"role": "semiconductor_sector_proxy", "basis_risk": "sector_basket_mix"},
    "NVDA": {"role": "semiconductor_single_name", "basis_risk": "company_specific_risk"},
    "TSM": {"role": "semiconductor_single_name", "basis_risk": "company_and_country_risk"},
    "QQQ": {"role": "technology_benchmark_proxy", "basis_risk": "broad_technology_beta"},
    "SLV": {"role": "silver_execution_proxy", "basis_risk": "trust_and_spot_basis"},
    "SIL": {"role": "silver_miner_proxy", "basis_risk": "equity_and_operating_leverage"},
    "GLD": {"role": "gold_macro_benchmark", "basis_risk": "cross_metal_proxy"},
    "SPY": {"role": "broad_market_benchmark", "basis_risk": "broad_beta_only"},
}


def evidence_profile_for_strategy(strategy_family_id: str | None) -> str:
    family = str(strategy_family_id or "")
    if family in EVENT_FAMILIES:
        return "event_catalyst"
    if family in REGIME_FAMILIES:
        return "regime_state"
    if family == PREDICTION_FAMILY:
        return "market_dislocation"
    return "research_relationship"


def discovery_micro_policy(policy: dict[str, Any]) -> dict[str, Any]:
    value = policy.get("discovery_micro_admission")
    return value if isinstance(value, dict) else {}


def trusted_fresh_support_sources(
    source_path: list[dict[str, Any]], policy: dict[str, Any]
) -> list[dict[str, Any]]:
    micro = discovery_micro_policy(policy)
    trust_floor = safe_float(micro.get("minimum_support_source_trust") or 0.55)
    rows = [
        row
        for row in source_path
        if isinstance(row, dict)
        and row.get("fresh") is True
        and safe_float(row.get("trust_score")) >= trust_floor
    ]
    return sorted(rows, key=lambda row: str(row.get("source_key") or ""))


def adapt_discovery_blockers(
    blockers: list[str],
    source_path: list[dict[str, Any]],
    policy: dict[str, Any],
) -> tuple[list[str], dict[str, Any]]:
    """Align pattern admission with the frozen evidence-fit policy.

    This can remove only requirements that the policy explicitly marks as
    optional. It cannot invent freshness, trust, confirmation, or quorum.
    """

    micro = discovery_micro_policy(policy)
    trusted = trusted_fresh_support_sources(source_path, policy)
    minimum = int(micro.get("minimum_fresh_support_sources") or 1)
    adapted = list(blockers)
    removed: list[str] = []
    if (
        micro.get("source_quorum_eligible_required") is False
        and len(trusted) >= minimum
        and "fresh_source_quorum" in adapted
    ):
        adapted.remove("fresh_source_quorum")
        removed.append("fresh_source_quorum")
    if micro.get("volume_or_flow_required") is False:
        for blocker in ("volume_or_flow_context", "volume_or_flow_missing"):
            if blocker in adapted:
                adapted.remove(blocker)
                removed.append(blocker)
    quorum = [row for row in trusted if row.get("quorum_eligible") is True]
    return sorted(set(adapted)), {
        "trusted_fresh_support_source_count": len(trusted),
        "trusted_fresh_support_source_keys": [row.get("source_key") for row in trusted],
        "fresh_quorum_source_count": len(quorum),
        "fresh_quorum_source_keys": [row.get("source_key") for row in quorum],
        "non_quorum_support_used": bool(trusted and len(quorum) < len(trusted)),
        "non_quorum_support_claimed_as_quorum": False,
        "policy_optional_blockers_removed": sorted(set(removed)),
    }


def market_records(market_context: dict[str, Any]) -> dict[str, dict[str, Any]]:
    for packet in market_context.get("recent_packets", []):
        if not isinstance(packet, dict) or packet.get("packet_role") != (
            "universal_current_market_context"
        ):
            continue
        payload = packet.get("price_volume_context")
        payload = payload if isinstance(payload, dict) else {}
        return {
            str(row.get("symbol") or "").upper(): row
            for row in payload.get("records", [])
            if isinstance(row, dict) and row.get("symbol")
        }
    return {}


def _horizon_days(value: Any) -> int:
    match = re.search(r"(\d+)", str(value or ""))
    return max(1, min(int(match.group(1)), 10)) if match else 5


def _historical_directional_prior(
    historical_result: dict[str, Any], direction: str
) -> float | None:
    value = historical_result.get("mean_net_return")
    if value is None or direction not in ACTIONABLE_DIRECTIONS:
        return None
    signed = safe_float(value)
    adjusted = signed if direction == "long" else -signed
    return adjusted if adjusted > 0 else None


def build_current_expectancy_v2(
    candidate: dict[str, Any],
    direction_resolution: dict[str, Any],
    market_record: dict[str, Any],
    historical_result: dict[str, Any],
    policy: dict[str, Any],
    *,
    generated_at: str,
) -> dict[str, Any]:
    """Build a conservative current expectancy for one paper experiment.

    The estimate is intentionally bounded by observed volatility and current
    execution friction. A rejected historical result may contribute a small,
    capped prior but is never required and never becomes edge proof.
    """

    micro = discovery_micro_policy(policy)
    direction = str(direction_resolution.get("actionable_direction") or "")
    symbol = str(candidate.get("instrument") or "").upper()
    blockers: list[str] = []
    if direction not in ACTIONABLE_DIRECTIONS:
        blockers.append("direction_unresolved")
    actionable_session = bool(
        market_record.get("provider_backed") is True
        and (
            market_record.get("quote_actionable") is True
            or market_record.get("trade_actionable") is True
        )
        and str(market_record.get("session_state") or "").lower()
        in {"regular", "regular_session", "open", "live"}
    )
    if not actionable_session:
        blockers.append("actionable_current_market_context_missing")
    current_price = safe_float(market_record.get("current_price"))
    if current_price <= 0:
        blockers.append("current_price_missing")
    volatility = safe_float(market_record.get("rolling_volatility_20d"))
    if volatility <= 0:
        annualized = safe_float(market_record.get("annualized_volatility"))
        volatility = annualized / sqrt(252) if annualized > 0 else 0.0
    if volatility <= 0:
        blockers.append("current_volatility_missing")
    spread_bps_value = market_record.get("spread_bps")
    if spread_bps_value is None:
        blockers.append("current_spread_missing")
    spread_bps = max(0.0, safe_float(spread_bps_value))

    move = safe_float(market_record.get("percent_move"))
    market_direction = "long" if move > 0 else "short" if move < 0 else None
    minimum_move = 0.05
    direction_aligned = bool(
        market_direction == direction and abs(move) >= minimum_move
    )
    volume_ratio = safe_float(market_record.get("volume_ratio"))
    volume_confirmation = volume_ratio >= 0.35
    confirmation_alternatives = []
    if direction_aligned:
        confirmation_alternatives.append("pricing_gap_evidence")
    if volume_confirmation:
        confirmation_alternatives.append("volume_or_flow_confirmation")
    required_confirmations = int(micro.get("minimum_confirmation_alternatives") or 1)
    if len(confirmation_alternatives) < required_confirmations:
        blockers.append("independent_live_market_confirmation_missing")

    rank = max(0.0, min(1.0, safe_float(candidate.get("research_rank"))))
    causal = direction_resolution.get("causal_classification")
    causal = causal if isinstance(causal, dict) else {}
    causal_confidence = max(0.0, min(1.0, safe_float(causal.get("confidence") or 0.55)))
    days = _horizon_days(candidate.get("horizon") or candidate.get("horizon_hypothesis"))
    expected_abs_move = volatility * sqrt(days) if volatility > 0 else 0.0
    capture_rate = min(0.35, 0.08 + 0.12 * rank + 0.10 * causal_confidence)
    current_gross = expected_abs_move * capture_rate if direction_aligned else 0.0

    prior = _historical_directional_prior(historical_result, direction)
    capped_prior = min(prior or 0.0, expected_abs_move * 0.25)
    gross_expectancy = (
        current_gross * 0.8 + capped_prior * 0.2 if prior is not None else current_gross
    )
    spread_cost = spread_bps / 10000.0
    slippage_cost = max(0.0002, spread_cost * 0.50)
    role = INSTRUMENT_ROLES.get(symbol, {"role": "listed_instrument", "basis_risk": "unclassified"})
    basis_cost = 0.0002 if "proxy" in role["role"] else 0.0001
    total_cost = spread_cost + slippage_cost + basis_cost
    net_expectancy = gross_expectancy - total_cost
    if not blockers and net_expectancy <= 0:
        blockers.append("positive_current_expectancy_after_costs_missing")

    status = (
        "ready_for_discovery_micro_review"
        if not blockers
        else "pending_current_market_context"
        if any(
            item in blockers
            for item in {
                "actionable_current_market_context_missing",
                "current_price_missing",
                "current_volatility_missing",
                "current_spread_missing",
                "independent_live_market_confirmation_missing",
            }
        )
        else "rejected_current_economics"
    )
    expectancy_id = stable_id(
        "current-expectancy-v2",
        candidate.get("pattern_relationship_id"),
        direction_resolution.get("direction_resolution_id"),
        market_record.get("quote_observed_at") or market_record.get("available_at"),
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_current_expectancy_v2",
        "generated_at": generated_at,
        "current_expectancy_id": expectancy_id,
        "pattern_relationship_id": candidate.get("pattern_relationship_id"),
        "score_id": candidate.get("score_id"),
        "strategy_family_id": candidate.get("strategy_family_id"),
        "instrument": symbol,
        "direction": direction,
        "status": status,
        "ready_for_discovery_micro_review": not blockers,
        "blockers": sorted(set(blockers)),
        "research_score": rank,
        "research_score_is_probability": False,
        "causal_confidence": causal_confidence,
        "current_market": {
            "provider": market_record.get("provider") or market_record.get("source"),
            "provider_backed": market_record.get("provider_backed") is True,
            "session_state": market_record.get("session_state"),
            "current_price": current_price or None,
            "percent_move": move,
            "volume_ratio": volume_ratio,
            "rolling_volatility_20d": volatility or None,
            "spread_bps": spread_bps_value,
            "observed_at": market_record.get("quote_observed_at")
            or market_record.get("last_trade_observed_at")
            or market_record.get("available_at"),
        },
        "instrument_expression": role,
        "confirmation": {
            "direction_aligned": direction_aligned,
            "alternatives_present": sorted(confirmation_alternatives),
            "minimum_alternatives": required_confirmations,
        },
        "economics": {
            "expected_abs_move": round(expected_abs_move, 8),
            "capture_rate": round(capture_rate, 8),
            "current_gross_expectancy": round(current_gross, 8),
            "historical_rejected_result_prior": round(prior, 8) if prior is not None else None,
            "historical_prior_capped": round(capped_prior, 8) if prior is not None else None,
            "gross_expectancy": round(gross_expectancy, 8),
            "spread_cost": round(spread_cost, 8),
            "slippage_cost": round(slippage_cost, 8),
            "proxy_basis_cost": round(basis_cost, 8),
            "total_cost": round(total_cost, 8),
            "net_expectancy": round(net_expectancy, 8),
            "minimum_reward_to_risk": safe_float(
                micro.get("minimum_current_reward_to_risk") or 1.25
            ),
        },
        "historical_expectancy_required": micro.get(
            "positive_historical_expectancy_required"
        )
        is True,
        "validated_edge_required": micro.get("validated_edge_required") is True,
        "not_validated_expectancy": True,
        "not_edge_proof": True,
        "not_execution_approval": True,
        "paper_order_created": False,
        "authority": authority_flags(),
    }


def build_calibration_state(
    funnel_rows: list[dict[str, Any]],
    eligible_days: list[dict[str, Any]],
    *,
    generated_at: str,
    required_sessions: int = 5,
) -> dict[str, Any]:
    eligible_ids = {
        str(row.get("session_id") or "")
        for row in eligible_days
        if row.get("eligible_for_conversion_measurement") is True
    }
    rows = [row for row in funnel_rows if str(row.get("session_id") or "") in eligible_ids]
    sessions = len(eligible_ids)
    totals = {
        field: sum(int(row.get(field) or 0) for row in rows)
        for field in (
            "instrument_evaluations",
            "shortlisted",
            "hypotheses",
            "akber_reviews",
            "akber_passes",
            "shadow_snapshots",
            "risk_proposals",
            "router_reviews",
            "paper_handoffs",
        )
    }
    proposals: list[dict[str, Any]] = []
    if sessions >= required_sessions:
        if totals["shortlisted"] and totals["hypotheses"] == 0:
            proposals.append(
                {
                    "proposal": "review_pre_akber_conversion_contract",
                    "reason": "shortlisted_setups_never_became_hypotheses",
                }
            )
        if totals["hypotheses"] and totals["akber_reviews"] == 0:
            proposals.append(
                {
                    "proposal": "review_decision_packet_contract",
                    "reason": "hypotheses_never_reached_akber",
                }
            )
        if totals["akber_reviews"] and totals["akber_passes"] == 0:
            proposals.append(
                {
                    "proposal": "run_profile_specific_akber_ablation_review",
                    "reason": "all_real_session_reviews_held_or_vetoed",
                }
            )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_discovery_micro_calibration",
        "generated_at": generated_at,
        "status": "proposal_ready" if sessions >= required_sessions else "pending_real_market_sessions",
        "eligible_real_market_sessions": sessions,
        "required_real_market_sessions": required_sessions,
        "empirical_window_complete": sessions >= required_sessions,
        "totals": totals,
        "proposals": proposals,
        "proposal_only": True,
        "automatic_threshold_mutation_allowed": False,
        "automatic_risk_or_authority_mutation_allowed": False,
        "simulated_or_backfilled_sessions_used": False,
        "paper_order_created": False,
        "authority": authority_flags(),
    }


__all__ = [
    "CALIBRATION_ARTIFACT",
    "CERTIFICATION_ARTIFACT",
    "CURRENT_EXPECTANCY_ARTIFACT",
    "DIRECTION_RETRY_ARTIFACT",
    "adapt_discovery_blockers",
    "build_calibration_state",
    "build_current_expectancy_v2",
    "discovery_micro_policy",
    "evidence_profile_for_strategy",
    "market_records",
    "trusted_fresh_support_sources",
]
