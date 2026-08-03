"""OR-14 deterministic portfolio construction and risk proposals.

The engine bounds hypothetical exposure using reviewed numeric rules. Its
output is proposal-only and cannot approve risk, call PaperOps, or create an
order. LLM and quantum fields are deliberately excluded from sizing authority.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import math
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_experimental_paper_policy import (
    DISCOVERY_MICRO_TIER,
    EXPERIMENTAL_UNVALIDATED,
    VALIDATED_PAPER_STRATEGY,
    experimental_tier,
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
from orchestrator.qadam_wave_b_common import parse_timestamp, safe_float, stable_id

SCHEMA_VERSION = "qadam_portfolio_risk_engine.v3"
PHASE_ID = "OR-14"
POLICY_VERSION = "qadam-paper-portfolio-risk.4-active-discovery-trial"

POLICY_ARTIFACT = "qadam_portfolio_policy.json"
RISK_STATE_ARTIFACT = "qadam_portfolio_risk_state.json"
PROPOSALS_ARTIFACT = "qadam_position_size_proposals.jsonl"
STRESS_TEST_ARTIFACT = "qadam_portfolio_stress_test.json"
REJECTIONS_ARTIFACT = "qadam_risk_rejections.jsonl"
CHECK_ARTIFACT = "qadam_portfolio_risk_engine_checks.json"

HYPOTHESES_ARTIFACT = "qadam_strategy_hypotheses_v3.jsonl"
EDGE_REGISTRY_ARTIFACT = "qadam_edge_registry.jsonl"
AKBER_INPUTS_ARTIFACT = "qadam_akber_filter_v3_inputs.jsonl"
AKBER_RESULTS_ARTIFACT = "qadam_akber_filter_v3_results.jsonl"
AKBER_REPLAY_ARTIFACT = "qadam_akber_filter_v3_replay.jsonl"
SHADOW_DECISIONS_ARTIFACT = "qadam_forward_shadow_decisions.jsonl"
SHADOW_OUTCOMES_ARTIFACT = "qadam_forward_shadow_outcomes.jsonl"
SHADOW_PROMOTION_ARTIFACT = "qadam_shadow_promotion_readiness.json"
CURRENT_PORTFOLIO_ARTIFACT = "qsase_dashboard_current_portfolio.json"
TRADING_UNIVERSE_ARTIFACT = "qsase_trading_universe.json"
ACCOUNT_SNAPSHOTS_ARTIFACT = "paper_account_snapshots.jsonl"
PAPER_ORDERS_ARTIFACT = "paper_orders.jsonl"
PAPEROPS_SUMMARY_ARTIFACT = "paperops_autonomous_pass_summary.json"

INITIAL_PAPER_BUDGET_USD = 100_000.0
ABSOLUTE_TRADE_CEILING_USD = 5_000.0
DISCOVERY_MICRO_TRADE_CEILING_USD = 5_000.0
DISCOVERY_TARGET_NOTIONAL_MIN_USD = 500.0
DISCOVERY_TARGET_NOTIONAL_MAX_USD = 1_000.0
MAXIMUM_CONCURRENT_DISCOVERY_POSITIONS = 3
MAXIMUM_DISCOVERY_POSITIONS_PER_CLUSTER = 1
DISCOVERY_MICRO_CONFIDENCE_CLASS = "experimental_discovery_micro"
MARKET_CONTEXT_MAX_AGE_SECONDS = 30 * 60
CANONICAL_DISCOVERY_ORDER_PREFIXES = ("q7-6-stage-",)
OPEN_ORDER_STATUSES = {
    "new",
    "accepted",
    "pending_new",
    "partially_filled",
    "held",
    "open",
}
ENTRY_POSITION_INTENTS = {
    "buy_to_open",
    "sell_short",
    "sell_to_open",
}

TAIL_SHOCKS_BY_CLUSTER = {
    "crude_oil": 0.18,
    "defence": 0.12,
    "prediction_markets": 0.25,
    "semiconductors": 0.20,
    "silver": 0.16,
    "macro": 0.15,
    "unknown": 0.25,
}


def default_portfolio_policy(generated_at: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_portfolio_policy",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": "frozen_research_policy",
        "policy_version": POLICY_VERSION,
        "scope": "paper_research_position_size_proposals_only",
        "capital_reference": {
            "initial_paper_budget_usd": INITIAL_PAPER_BUDGET_USD,
            "absolute_trade_ceiling_usd": ABSOLUTE_TRADE_CEILING_USD,
            "absolute_trade_ceiling_is_operator_reviewed": True,
        },
        "risk_budget": {
            "max_risk_per_position_pct_equity": 0.005,
            "max_position_notional_usd": ABSOLUTE_TRADE_CEILING_USD,
            "discovery_micro_trade_ceiling_usd": DISCOVERY_MICRO_TRADE_CEILING_USD,
            "discovery_target_notional_usd": {
                "minimum": DISCOVERY_TARGET_NOTIONAL_MIN_USD,
                "maximum": DISCOVERY_TARGET_NOTIONAL_MAX_USD,
                "minimum_is_not_a_forced_floor": True,
            },
            "maximum_concurrent_discovery_micro_positions": MAXIMUM_CONCURRENT_DISCOVERY_POSITIONS,
            "maximum_discovery_positions_per_correlated_cluster": MAXIMUM_DISCOVERY_POSITIONS_PER_CLUSTER,
            "max_instrument_notional_pct_equity": 0.05,
            "max_strategy_notional_pct_equity": 0.15,
            "max_correlated_cluster_notional_pct_equity": 0.20,
            "max_source_family_notional_pct_equity": 0.20,
            "max_high_correlation_notional_pct_equity": 0.10,
            "max_gross_notional_pct_equity": 0.40,
            "max_new_notional_per_day_pct_equity": 0.20,
            "max_daily_loss_pct_equity": 0.02,
            "max_trailing_drawdown_pct_equity": 0.08,
            "max_tail_stress_loss_pct_equity": 0.04,
            "max_source_concentration": 0.50,
            "high_correlation_threshold": 0.70,
            "max_pairwise_absolute_correlation": 0.95,
        },
        "market_quality": {
            "maximum_spread_bps": 100.0,
            "maximum_adv_participation": 0.001,
            "minimum_expected_net_return": 0.0,
            "maximum_uncertainty": 0.50,
            "annualized_volatility_target": 0.12,
            "maximum_market_context_age_seconds": MARKET_CONTEXT_MAX_AGE_SECONDS,
        },
        "confidence_classes": {
            "validated_research_edge": {
                "risk_multiplier": 1.0,
                "uncertainty_haircut": 0.25,
            },
            "exploratory_research_edge": {
                "risk_multiplier": 0.0,
                "uncertainty_haircut": 1.0,
            },
            EXPERIMENTAL_UNVALIDATED: {
                "risk_multiplier": 0.50,
                "uncertainty_haircut": 0.50,
            },
            DISCOVERY_MICRO_CONFIDENCE_CLASS: {
                "risk_multiplier": 0.10,
                "uncertainty_haircut": 0.75,
            },
        },
        "tail_stress": {
            "cluster_loss_shocks": TAIL_SHOCKS_BY_CLUSTER,
            "unclassified_position_uses_conservative_shock": True,
            "stress_test_is_not_forecast": True,
        },
        "context_derivation": {
            "contract_version": "portfolio-context-derivation.v1",
            "broker_entry_orders_are_daily_notional_source": True,
            "protective_exit_orders_are_not_new_notional": True,
            "unlabelled_positions_use_conservative_sleeve_classification": True,
            "missing_pairwise_correlation_uses_cluster_proxy": True,
            "same_instrument_proxy_correlation": 1.0,
            "same_cluster_proxy_correlation": 0.85,
            "unknown_or_broad_cluster_proxy_correlation": 0.70,
            "different_cluster_proxy_correlation": 0.35,
            "derived_context_can_reduce_missing_data_holds_but_not_numeric_limits": True,
        },
        "rounding": {
            "default_quantity_increment": 1.0,
            "fractional_quantity_allowed_only_when_instrument_contract_says_so": True,
            "always_round_down": True,
        },
        "hard_fail_closed_inputs": [
            "portfolio_equity",
            "current_price",
            "invalidation_price_or_max_loss_per_unit",
            "expected_net_return_after_costs",
            "annualized_volatility",
            "liquidity_and_spread",
            "current_daily_loss",
            "trailing_drawdown",
            "paperability",
            "correlated_cluster",
            "edge_confidence_class",
            "uncertainty_haircut",
            "source_family_context",
            "cross_position_correlation_when_positions_exist",
            "daily_new_notional_context",
            "fresh_market_context",
        ],
        "change_control": {
            "human_governed": True,
            "explicit_versioned_review_required": True,
            "automated_policy_changes_allowed": False,
            "llm_policy_changes_allowed": False,
            "quantum_policy_changes_allowed": False,
            "implementation_baseline_is_not_execution_approval": True,
        },
        "authority": authority_flags(),
    }


def _positions(portfolio: dict[str, Any]) -> list[dict[str, Any]]:
    rows = portfolio.get("positions")
    if not isinstance(rows, list):
        rows = portfolio.get("rows")
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _position_notional(position: dict[str, Any]) -> float:
    for field in ("notional", "market_value", "current_value"):
        if position.get(field) is not None:
            return abs(safe_float(position.get(field)))
    return abs(safe_float(position.get("quantity")) * safe_float(position.get("price")))


def _source_families(record: dict[str, Any]) -> list[str]:
    values = record.get("source_families")
    if not isinstance(values, list):
        value = record.get("dominant_source_family")
        values = [value] if value else []
    return sorted({str(value) for value in values if value})


def _exposure_totals(portfolio: dict[str, Any]) -> dict[str, Any]:
    by_instrument: Counter[str] = Counter()
    by_strategy: Counter[str] = Counter()
    by_cluster: Counter[str] = Counter()
    by_source_family: Counter[str] = Counter()
    gross = 0.0
    unclassified_position_count = 0
    for position in _positions(portfolio):
        notional = _position_notional(position)
        gross += notional
        instrument = str(position.get("instrument") or position.get("symbol") or "unknown")
        strategy = str(position.get("strategy_family_id") or "unknown")
        cluster = str(position.get("correlated_cluster") or "unknown")
        families = _source_families(position)
        by_instrument[instrument] += notional
        by_strategy[strategy] += notional
        by_cluster[cluster] += notional
        for family in families:
            by_source_family[family] += notional
        if instrument == "unknown" or strategy == "unknown" or cluster == "unknown" or not families:
            unclassified_position_count += 1
    return {
        "gross_notional": gross,
        "by_instrument": dict(by_instrument),
        "by_strategy": dict(by_strategy),
        "by_correlated_cluster": dict(by_cluster),
        "by_source_family": dict(by_source_family),
        "unclassified_position_count": unclassified_position_count,
    }


def _correlation_records(setup: dict[str, Any]) -> list[dict[str, Any]]:
    rows = setup.get("correlation_to_existing")
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _complete_correlation_context(
    setup: dict[str, Any], portfolio: dict[str, Any]
) -> dict[str, Any]:
    """Fill absent pairwise context with conservative, labelled cluster proxies."""

    completed = dict(setup)
    positions = _positions(portfolio)
    if not positions:
        completed["correlation_to_existing"] = _correlation_records(setup)
        completed["correlation_context_basis"] = "not_required_no_existing_positions"
        completed["derived_correlation_record_count"] = 0
        return completed

    direct = {
        str(row.get("instrument") or ""): dict(row)
        for row in _correlation_records(setup)
        if row.get("instrument") and row.get("correlation") is not None
    }
    instrument = str(setup.get("instrument") or "")
    cluster = str(setup.get("correlated_cluster") or "unknown")
    derived_count = 0
    for position in positions:
        existing = str(position.get("instrument") or position.get("symbol") or "")
        if not existing or existing in direct:
            continue
        existing_cluster = str(position.get("correlated_cluster") or "unknown")
        if existing == instrument:
            correlation = 1.0
            basis = "same_instrument_conservative_proxy"
        elif cluster == existing_cluster and cluster not in {"", "unknown"}:
            correlation = 0.85
            basis = "same_market_cluster_conservative_proxy"
        elif (
            cluster in {"", "unknown", "whole_paperable_universe"}
            or existing_cluster in {"", "unknown", "whole_paperable_universe"}
        ):
            correlation = 0.70
            basis = "broad_or_unknown_cluster_conservative_proxy"
        else:
            correlation = 0.35
            basis = "different_market_cluster_conservative_proxy"
        direct[existing] = {
            "instrument": existing,
            "correlation": correlation,
            "basis": basis,
            "direct_measurement": False,
            "conservative_fallback": True,
        }
        derived_count += 1
    completed["correlation_to_existing"] = [direct[key] for key in sorted(direct)]
    completed["correlation_context_basis"] = (
        "direct_and_conservative_cluster_proxy"
        if derived_count and derived_count < len(direct)
        else "conservative_cluster_proxy"
        if derived_count
        else "direct_pairwise_measurement"
    )
    completed["derived_correlation_record_count"] = derived_count
    return completed


def _correlation_context_complete(setup: dict[str, Any], portfolio: dict[str, Any]) -> bool:
    positions = _positions(portfolio)
    if not positions:
        return True
    rows = _correlation_records(setup)
    covered = {str(row.get("instrument") or "") for row in rows if row.get("correlation") is not None}
    required = {
        str(position.get("instrument") or position.get("symbol") or "")
        for position in positions
    }
    return bool(required) and required.issubset(covered)


def _high_correlation_exposure(
    setup: dict[str, Any], portfolio: dict[str, Any], policy: dict[str, Any]
) -> float:
    threshold = safe_float(policy["risk_budget"]["high_correlation_threshold"])
    high = {
        str(row.get("instrument") or "")
        for row in _correlation_records(setup)
        if abs(safe_float(row.get("correlation"))) >= threshold
    }
    return sum(
        _position_notional(position)
        for position in _positions(portfolio)
        if str(position.get("instrument") or position.get("symbol") or "") in high
    )


def _tail_shock_fraction(cluster: str, policy: dict[str, Any]) -> float:
    shocks = policy.get("tail_stress", {}).get("cluster_loss_shocks", {})
    return safe_float(shocks.get(cluster), safe_float(shocks.get("unknown"), 0.25))


def _estimated_tail_loss(portfolio: dict[str, Any], policy: dict[str, Any]) -> float:
    return sum(
        _position_notional(position)
        * _tail_shock_fraction(str(position.get("correlated_cluster") or "unknown"), policy)
        for position in _positions(portfolio)
    )


def _missing_or_invalid_inputs(
    setup: dict[str, Any], portfolio: dict[str, Any], policy: dict[str, Any]
) -> list[str]:
    reasons: list[str] = []
    equity = safe_float(portfolio.get("equity"), -1.0)
    price = safe_float(setup.get("current_price"), -1.0)
    volatility = safe_float(setup.get("annualized_volatility"), -1.0)
    invalidation = setup.get("invalidation")
    liquidity = setup.get("liquidity")
    if equity <= 0:
        reasons.append("portfolio_equity_missing_or_non_positive")
    if price <= 0:
        reasons.append("current_price_missing_or_non_positive")
    if volatility <= 0:
        reasons.append("annualized_volatility_missing_or_non_positive")
    if not isinstance(invalidation, dict):
        reasons.append("invalidation_context_missing")
    else:
        per_unit = safe_float(invalidation.get("max_loss_per_unit"), 0.0)
        invalidation_price = safe_float(invalidation.get("invalidation_price"), 0.0)
        if per_unit <= 0 and invalidation_price <= 0:
            reasons.append("invalidation_price_or_max_loss_per_unit_missing")
    if not isinstance(liquidity, dict):
        reasons.append("liquidity_and_spread_missing")
    else:
        if liquidity.get("spread_bps") is None:
            reasons.append("spread_context_missing")
        if safe_float(liquidity.get("average_daily_dollar_volume"), 0.0) <= 0:
            reasons.append("average_daily_dollar_volume_missing")
    if setup.get("expected_net_return") is None:
        reasons.append("expected_net_return_after_costs_missing")
    if not setup.get("edge_confidence_class"):
        reasons.append("edge_confidence_class_missing")
    if setup.get("uncertainty") is None or not 0 <= safe_float(
        setup.get("uncertainty"), -1.0
    ) <= 1:
        reasons.append("uncertainty_haircut_missing")
    if setup.get("market_context_fresh") is not True:
        reasons.append("fresh_market_context_missing")
    if setup.get("market_context_age_seconds") is None:
        reasons.append("market_context_age_missing")
    if portfolio.get("daily_loss_pct") is None:
        reasons.append("current_daily_loss_missing")
    if portfolio.get("trailing_drawdown_pct") is None:
        reasons.append("trailing_drawdown_missing")
    if portfolio.get("new_notional_today") is None:
        reasons.append("daily_new_notional_context_missing")
    if setup.get("paperable") is not True:
        reasons.append("paperability_not_confirmed")
    if setup.get("paper_route") != "guarded_alpaca_paper_via_paperops":
        reasons.append("guarded_paper_route_not_confirmed")
    if safe_float(setup.get("quantity_increment"), 0.0) <= 0:
        reasons.append("broker_quantity_increment_missing_or_invalid")
    if not setup.get("correlated_cluster"):
        reasons.append("correlated_cluster_missing")
    if not _source_families(setup):
        reasons.append("source_family_context_missing")
    if setup.get("source_concentration") is None:
        reasons.append("source_concentration_missing")
    if _positions(portfolio) and _exposure_totals(portfolio)["unclassified_position_count"]:
        reasons.append("existing_exposure_classification_incomplete")
    if not _correlation_context_complete(setup, portfolio):
        reasons.append("cross_position_correlation_context_missing")
    if setup.get("akber_decision") != "pass":
        reasons.append("akber_pass_missing")
    evidence_class = str(
        setup.get("evidence_class") or VALIDATED_PAPER_STRATEGY
    )
    if evidence_class == EXPERIMENTAL_UNVALIDATED:
        tier = experimental_tier(setup)
        if setup.get("decision_time_shadow_snapshot_ready") is not True:
            reasons.append("decision_time_shadow_snapshot_not_ready")
        if setup.get("edge_id"):
            reasons.append("experimental_setup_claimed_validated_edge")
        if tier == DISCOVERY_MICRO_TIER and int(
            portfolio.get("open_discovery_micro_exposure_count") or 0
        ) >= int(
            policy.get("risk_budget", {}).get(
                "maximum_concurrent_discovery_micro_positions",
                MAXIMUM_CONCURRENT_DISCOVERY_POSITIONS,
            )
        ):
            reasons.append("discovery_micro_concurrent_position_limit_reached")
        if tier == DISCOVERY_MICRO_TIER:
            cluster = str(setup.get("correlated_cluster") or "unknown")
            occupied_clusters = set(
                portfolio.get("open_discovery_micro_clusters") or []
            )
            if cluster in occupied_clusters:
                reasons.append("discovery_micro_correlated_cluster_slot_occupied")
    elif setup.get("shadow_promotion_ready") is not True:
        reasons.append("forward_shadow_promotion_not_ready")
    if policy.get("policy_version") != POLICY_VERSION:
        reasons.append("portfolio_policy_version_unrecognized")
    return unique_errors(reasons)


def _policy_vetoes(
    setup: dict[str, Any], portfolio: dict[str, Any], policy: dict[str, Any]
) -> list[str]:
    reasons: list[str] = []
    risk = policy["risk_budget"]
    market = policy["market_quality"]
    expected_net = safe_float(setup.get("expected_net_return"), 0.0)
    if expected_net <= safe_float(market["minimum_expected_net_return"]):
        reasons.append("expected_return_non_positive_after_costs")
    uncertainty = safe_float(setup.get("uncertainty"), 1.0)
    confidence_class = str(setup.get("edge_confidence_class") or "")
    class_uncertainty = safe_float(
        policy.get("confidence_classes", {})
        .get(confidence_class, {})
        .get("uncertainty_haircut"),
        0.0,
    )
    maximum_uncertainty = max(
        safe_float(market["maximum_uncertainty"]), class_uncertainty
    )
    if uncertainty > maximum_uncertainty:
        reasons.append("uncertainty_exceeds_frozen_maximum")
    liquidity = setup.get("liquidity") if isinstance(setup.get("liquidity"), dict) else {}
    spread_bps = safe_float(liquidity.get("spread_bps"), float("inf"))
    if spread_bps > safe_float(market["maximum_spread_bps"]):
        reasons.append("spread_exceeds_frozen_maximum")
    daily_loss = safe_float(portfolio.get("daily_loss_pct"), 1.0)
    if daily_loss >= safe_float(risk["max_daily_loss_pct_equity"]):
        reasons.append("daily_loss_gate_breached")
    drawdown = safe_float(portfolio.get("trailing_drawdown_pct"), 1.0)
    if drawdown >= safe_float(risk["max_trailing_drawdown_pct_equity"]):
        reasons.append("trailing_drawdown_gate_breached")
    source_concentration = safe_float(setup.get("source_concentration"), 1.0)
    if source_concentration > safe_float(risk["max_source_concentration"]):
        reasons.append("source_concentration_exceeds_maximum")
    context_age = safe_float(setup.get("market_context_age_seconds"), float("inf"))
    if context_age > safe_float(market["maximum_market_context_age_seconds"]):
        reasons.append("market_context_exceeds_frozen_maximum_age")
    confidence = str(setup.get("edge_confidence_class") or "")
    confidence_policy = policy.get("confidence_classes", {}).get(confidence, {})
    if safe_float(confidence_policy.get("risk_multiplier"), 0.0) <= 0:
        reasons.append("edge_confidence_class_not_sizeable")
    max_correlation = max(
        (abs(safe_float(row.get("correlation"))) for row in _correlation_records(setup)),
        default=0.0,
    )
    if max_correlation > safe_float(risk["max_pairwise_absolute_correlation"]):
        reasons.append("pairwise_correlation_exceeds_frozen_maximum")
    return unique_errors(reasons)


def _round_down(value: float, increment: float) -> float:
    if increment <= 0:
        raise ValueError("quantity_increment_must_be_positive")
    units = math.floor((value + 1e-12) / increment)
    return round(units * increment, 10)


def evaluate_position_size(
    setup: dict[str, Any],
    portfolio: dict[str, Any],
    policy: dict[str, Any],
    *,
    generated_at: str,
) -> dict[str, Any]:
    """Return exactly one proposal or one fail-closed risk rejection."""

    setup_id = str(setup.get("setup_id") or setup.get("hypothesis_id") or "")
    if not setup_id:
        raise ValueError("risk_setup_id_missing")
    setup = _complete_correlation_context(setup, portfolio)
    reasons = _missing_or_invalid_inputs(setup, portfolio, policy)
    reasons = unique_errors(reasons + _policy_vetoes(setup, portfolio, policy))
    if reasons:
        rejection = {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_risk_rejection",
            "phase_id": PHASE_ID,
            "generated_at": generated_at,
            "rejection_id": stable_id("risk-rejection-v3", setup_id, reasons),
            "setup_id": setup_id,
            "hypothesis_id": setup.get("hypothesis_id"),
            "evidence_class": setup.get("evidence_class"),
            "experimental_tier": experimental_tier(setup),
            "edge_id": setup.get("edge_id"),
            "pattern_relationship_id": setup.get("pattern_relationship_id"),
            "score_id": setup.get("score_id"),
            "rejection_reasons": reasons,
            "position_size_proposed": False,
            "risk_approval_created": False,
            "paper_order_created": False,
            "authority": authority_flags(),
        }
        return {"proposal": None, "rejection": rejection}

    equity = safe_float(portfolio["equity"])
    price = safe_float(setup["current_price"])
    volatility = safe_float(setup["annualized_volatility"])
    uncertainty = safe_float(setup.get("uncertainty"), 0.0)
    confidence_class = str(setup.get("edge_confidence_class"))
    confidence_multiplier = safe_float(
        policy["confidence_classes"][confidence_class]["risk_multiplier"]
    )
    invalidation = setup["invalidation"]
    max_loss_per_unit = safe_float(invalidation.get("max_loss_per_unit"), 0.0)
    if max_loss_per_unit <= 0:
        max_loss_per_unit = abs(price - safe_float(invalidation["invalidation_price"]))
    policy_risk = policy["risk_budget"]
    market = policy["market_quality"]
    liquidity = setup["liquidity"]
    risk_dollars = (
        equity
        * safe_float(policy_risk["max_risk_per_position_pct_equity"])
        * confidence_multiplier
        * max(0.0, 1.0 - uncertainty)
    )
    by_risk = risk_dollars / max_loss_per_unit
    exposures = _exposure_totals(portfolio)
    instrument = str(setup.get("instrument"))
    strategy = str(setup.get("strategy_family_id"))
    cluster = str(setup.get("correlated_cluster"))
    source_families = _source_families(setup)
    current_tail_loss = _estimated_tail_loss(portfolio, policy)
    tail_shock = _tail_shock_fraction(cluster, policy)

    def remaining(cap_pct: float, used: float) -> float:
        return max(0.0, equity * cap_pct - used)

    notional_limits = {
        "absolute_trade_ceiling": safe_float(policy_risk["max_position_notional_usd"]),
        "instrument": remaining(
            safe_float(policy_risk["max_instrument_notional_pct_equity"]),
            safe_float(exposures["by_instrument"].get(instrument)),
        ),
        "strategy": remaining(
            safe_float(policy_risk["max_strategy_notional_pct_equity"]),
            safe_float(exposures["by_strategy"].get(strategy)),
        ),
        "correlated_cluster": remaining(
            safe_float(policy_risk["max_correlated_cluster_notional_pct_equity"]),
            safe_float(exposures["by_correlated_cluster"].get(cluster)),
        ),
        "source_family": min(
            remaining(
                safe_float(policy_risk["max_source_family_notional_pct_equity"]),
                safe_float(exposures["by_source_family"].get(source_family)),
            )
            for source_family in source_families
        ),
        "high_correlation": remaining(
            safe_float(policy_risk["max_high_correlation_notional_pct_equity"]),
            _high_correlation_exposure(setup, portfolio, policy),
        ),
        "gross": remaining(
            safe_float(policy_risk["max_gross_notional_pct_equity"]),
            safe_float(exposures["gross_notional"]),
        ),
        "daily_new_notional": remaining(
            safe_float(policy_risk["max_new_notional_per_day_pct_equity"]),
            safe_float(portfolio.get("new_notional_today")),
        ),
        "liquidity": safe_float(liquidity["average_daily_dollar_volume"])
        * safe_float(market["maximum_adv_participation"]),
        "volatility_target": equity
        * min(
            safe_float(policy_risk["max_instrument_notional_pct_equity"]),
            safe_float(market["annualized_volatility_target"]) / max(volatility, 1e-9),
        ),
        "tail_stress": max(
            0.0,
            (
                equity * safe_float(policy_risk["max_tail_stress_loss_pct_equity"])
                - current_tail_loss
            )
            / max(tail_shock, 1e-9),
        ),
    }
    if experimental_tier(setup) == DISCOVERY_MICRO_TIER:
        notional_limits["discovery_target_maximum"] = safe_float(
            policy_risk.get("discovery_target_notional_usd", {}).get("maximum")
        )
        notional_limits["discovery_micro_tier"] = safe_float(
            policy_risk["discovery_micro_trade_ceiling_usd"]
        )
    max_notional = min(notional_limits.values())
    by_notional = max_notional / price
    raw_quantity = min(by_risk, by_notional)
    increment = safe_float(
        setup.get("quantity_increment"),
        safe_float(policy["rounding"]["default_quantity_increment"]),
    )
    quantity = _round_down(raw_quantity, increment)
    if quantity <= 0:
        rejection = {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_risk_rejection",
            "phase_id": PHASE_ID,
            "generated_at": generated_at,
            "rejection_id": stable_id(
                "risk-rejection-v3", setup_id, "no_capacity_after_caps_and_rounding"
            ),
            "setup_id": setup_id,
            "hypothesis_id": setup.get("hypothesis_id"),
            "evidence_class": setup.get("evidence_class"),
            "experimental_tier": experimental_tier(setup),
            "edge_id": setup.get("edge_id"),
            "pattern_relationship_id": setup.get("pattern_relationship_id"),
            "score_id": setup.get("score_id"),
            "rejection_reasons": ["no_capacity_after_exposure_caps_and_broker_rounding"],
            "binding_limit": min(notional_limits, key=notional_limits.get),
            "position_size_proposed": False,
            "risk_approval_created": False,
            "paper_order_created": False,
            "authority": authority_flags(),
        }
        return {"proposal": None, "rejection": rejection}
    notional = quantity * price
    maximum_loss = quantity * max_loss_per_unit
    proposal = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_position_size_proposal",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "proposal_id": stable_id(
            "position-size-proposal-v3", setup_id, POLICY_VERSION, quantity
        ),
        "setup_id": setup_id,
        "hypothesis_id": setup.get("hypothesis_id"),
        "evidence_class": setup.get("evidence_class"),
        "experimental_tier": experimental_tier(setup),
        "edge_id": setup.get("edge_id"),
        "pattern_relationship_id": setup.get("pattern_relationship_id"),
        "score_id": setup.get("score_id"),
        "akber_result_id": setup.get("akber_result_id"),
        "shadow_evidence_id": setup.get("shadow_evidence_id"),
        "research_goal_id": setup.get("research_goal_id"),
        "policy_version": POLICY_VERSION,
        "instrument": instrument,
        "strategy_family_id": strategy,
        "correlated_cluster": cluster,
        "source_families": source_families,
        "paper_route": setup.get("paper_route"),
        "direction": setup.get("direction"),
        "proposed_quantity": quantity,
        "quantity_increment": increment,
        "quantity_rounded_down": True,
        "current_price": price,
        "proposed_notional": round(notional, 10),
        "discovery_target_notional_usd": policy_risk.get(
            "discovery_target_notional_usd"
        ),
        "below_discovery_target_minimum": bool(
            experimental_tier(setup) == DISCOVERY_MICRO_TIER
            and notional < DISCOVERY_TARGET_NOTIONAL_MIN_USD
        ),
        "maximum_loss_at_invalidation": round(maximum_loss, 10),
        "risk_budget_dollars_after_uncertainty_haircut": round(risk_dollars, 10),
        "edge_confidence_class": confidence_class,
        "confidence_class_risk_multiplier": confidence_multiplier,
        "expected_net_return": setup.get("expected_net_return"),
        "research_score": setup.get("research_score"),
        "annualized_volatility": volatility,
        "spread_bps": liquidity.get("spread_bps"),
        "average_daily_dollar_volume": liquidity.get(
            "average_daily_dollar_volume"
        ),
        "uncertainty_haircut": uncertainty,
        "notional_limits": {key: round(value, 10) for key, value in notional_limits.items()},
        "binding_limit": min(notional_limits, key=notional_limits.get),
        "existing_exposure": exposures,
        "cross_position_correlation_context_complete": _correlation_context_complete(
            setup, portfolio
        ),
        "correlation_context_basis": setup.get("correlation_context_basis"),
        "derived_correlation_record_count": setup.get(
            "derived_correlation_record_count", 0
        ),
        "maximum_pairwise_absolute_correlation": max(
            (
                abs(safe_float(row.get("correlation")))
                for row in _correlation_records(setup)
            ),
            default=0.0,
        ),
        "tail_stress_shock_fraction": tail_shock,
        "post_trade_estimated_tail_loss": round(
            current_tail_loss + notional * tail_shock, 10
        ),
        "proposal_only": True,
        "llm_size_input_used": False,
        "quantum_size_input_used": False,
        "risk_approval_created": False,
        "execution_approval_created": False,
        "paper_order_created": False,
        "authority": authority_flags(),
    }
    return {"proposal": proposal, "rejection": None}


def _latest_snapshot(records: list[dict[str, Any]]) -> dict[str, Any]:
    return max(
        (record for record in records if parse_timestamp(record.get("observed_at"))),
        key=lambda record: parse_timestamp(record.get("observed_at")) or datetime.min.replace(
            tzinfo=timezone.utc
        ),
        default={},
    )


def _order_identifier_values(order: dict[str, Any]) -> tuple[str, ...]:
    return tuple(
        str(order.get(field) or "")
        for field in ("client_order_id", "idempotency_key", "source_idempotency_key")
    )


def _is_canonical_discovery_order(order: dict[str, Any]) -> bool:
    if experimental_tier(order) == DISCOVERY_MICRO_TIER:
        return True
    return any(
        value.startswith(CANONICAL_DISCOVERY_ORDER_PREFIXES)
        for value in _order_identifier_values(order)
        if value
    )


def _is_entry_order(order: dict[str, Any]) -> bool:
    return str(order.get("position_intent") or "").lower() in ENTRY_POSITION_INTENTS


def _is_open_order(order: dict[str, Any]) -> bool:
    return str(order.get("status") or "").lower() in OPEN_ORDER_STATUSES


def _position_risk_classification(
    position: dict[str, Any], entry_orders: list[dict[str, Any]]
) -> dict[str, Any]:
    """Classify existing exposure without pretending unknown strategy lineage is known."""

    classified = dict(position)
    if classified.get("strategy_family_id") and _source_families(classified):
        classified["risk_classification_basis"] = "explicit_position_lineage"
        classified["risk_classification_is_estimated"] = False
        return classified

    latest_entry = max(
        entry_orders,
        key=lambda order: parse_timestamp(order.get("submitted_at") or order.get("created_at"))
        or datetime.min.replace(tzinfo=timezone.utc),
        default={},
    )
    identifiers = _order_identifier_values(latest_entry)
    if latest_entry and _is_canonical_discovery_order(latest_entry):
        sleeve = "canonical_discovery_micro"
        classified["experimental_tier"] = DISCOVERY_MICRO_TIER
    elif any(value.startswith("q7-operator-sleeve-") for value in identifiers):
        sleeve = "operator_exploratory_sleeve"
    else:
        sleeve = "unclassified_existing_paper_exposure"
    classified.setdefault("strategy_family_id", sleeve)
    if not _source_families(classified):
        classified["source_families"] = [sleeve]
    classified["risk_classification_basis"] = (
        "conservative_entry_order_lineage"
        if latest_entry
        else "conservative_unlabelled_position_fallback"
    )
    classified["risk_classification_is_estimated"] = True
    classified["risk_classification_label"] = sleeve
    return classified


def _current_portfolio_state(
    portfolio_view: dict[str, Any],
    account_snapshots: list[dict[str, Any]],
    paper_orders: list[dict[str, Any]],
    trading_universe: dict[str, Any],
    *,
    generated_at: str,
) -> dict[str, Any]:
    consistency = (
        portfolio_view.get("portfolio_consistency")
        if isinstance(portfolio_view.get("portfolio_consistency"), dict)
        else {}
    )
    latest = _latest_snapshot(account_snapshots)
    latest_at = parse_timestamp(latest.get("observed_at"))
    equity = safe_float(
        latest.get("equity_gbp"), safe_float(consistency.get("current_value"), -1.0)
    )
    peak = safe_float(latest.get("peak_equity_gbp"), 0.0)
    if peak <= 0:
        peak = max(
            [safe_float(row.get("equity_gbp"), 0.0) for row in account_snapshots]
            + [equity]
        )
    trailing_drawdown = max(0.0, (peak - equity) / peak) if peak > 0 and equity > 0 else None
    same_day = [
        row
        for row in account_snapshots
        if latest_at is not None
        and (observed := parse_timestamp(row.get("observed_at"))) is not None
        and observed.date() == latest_at.date()
    ]
    first_today = min(
        same_day,
        key=lambda row: parse_timestamp(row.get("observed_at"))
        or datetime.max.replace(tzinfo=timezone.utc),
        default={},
    )
    first_equity = safe_float(first_today.get("equity_gbp"), equity)
    daily_loss = (
        max(0.0, (first_equity - equity) / first_equity)
        if first_equity > 0 and equity > 0
        else None
    )
    universe_by_symbol = {
        str(row.get("symbol") or ""): row
        for row in trading_universe.get("instruments", [])
        if isinstance(row, dict) and row.get("symbol")
    }
    entry_orders_by_symbol: dict[str, list[dict[str, Any]]] = {}
    for order in paper_orders:
        symbol = str(order.get("instrument") or order.get("symbol") or "")
        status = str(order.get("status") or "").lower()
        if (
            symbol
            and _is_entry_order(order)
            and status in OPEN_ORDER_STATUSES.union({"filled", "partially_filled"})
        ):
            entry_orders_by_symbol.setdefault(symbol, []).append(order)
    positions: list[dict[str, Any]] = []
    for raw in _positions(portfolio_view):
        position = dict(raw)
        symbol = str(position.get("instrument") or position.get("symbol") or "")
        universe = universe_by_symbol.get(symbol, {})
        position.setdefault("instrument", symbol)
        position.setdefault("correlated_cluster", universe.get("market_family"))
        positions.append(
            _position_risk_classification(
                position, entry_orders_by_symbol.get(symbol, [])
            )
        )
    new_notional_today = 0.0
    daily_notional_complete = latest_at is not None
    open_order_count = 0
    for order in paper_orders:
        if _is_open_order(order):
            open_order_count += 1
        observed = parse_timestamp(order.get("submitted_at") or order.get("created_at"))
        if latest_at is None or observed is None or observed.date() != latest_at.date():
            continue
        if not _is_entry_order(order):
            continue
        status = str(order.get("status") or "").lower()
        if status not in OPEN_ORDER_STATUSES.union({"filled"}):
            continue
        price = safe_float(
            order.get("filled_avg_price"),
            safe_float(
                order.get("limit_price"), safe_float(order.get("stop_price"), 0.0)
            ),
        )
        quantity = safe_float(
            order.get("quantity"), safe_float(order.get("filled_quantity"), 0.0)
        )
        if price <= 0 and quantity > 0:
            price = safe_float(order.get("notional"), 0.0) / quantity
        if price <= 0 or quantity <= 0:
            daily_notional_complete = False
            continue
        new_notional_today += abs(price * quantity)
    canonical_micro_symbols = {
        str(position.get("instrument") or position.get("symbol") or "")
        for position in positions
        if experimental_tier(position) == DISCOVERY_MICRO_TIER
    }
    canonical_micro_symbols.update(
        str(order.get("instrument") or order.get("symbol") or "")
        for order in paper_orders
        if _is_open_order(order)
        and _is_entry_order(order)
        and _is_canonical_discovery_order(order)
    )
    canonical_micro_symbols.discard("")
    canonical_micro_clusters = {
        str(position.get("correlated_cluster") or "unknown")
        for position in positions
        if experimental_tier(position) == DISCOVERY_MICRO_TIER
    }
    canonical_micro_clusters.update(
        str(
            universe_by_symbol.get(
                str(order.get("instrument") or order.get("symbol") or ""), {}
            ).get("market_family")
            or "unknown"
        )
        for order in paper_orders
        if _is_open_order(order)
        and _is_entry_order(order)
        and _is_canonical_discovery_order(order)
    )
    derived_position_classification_count = sum(
        position.get("risk_classification_is_estimated") is True
        for position in positions
    )
    return {
        "equity": equity if equity > 0 else None,
        "daily_loss_pct": daily_loss,
        "trailing_drawdown_pct": trailing_drawdown,
        "new_notional_today": round(new_notional_today, 10)
        if daily_notional_complete
        else None,
        "positions": positions,
        "open_order_count": open_order_count,
        "open_discovery_micro_exposure_count": len(canonical_micro_symbols),
        "open_discovery_micro_symbols": sorted(canonical_micro_symbols),
        "open_discovery_micro_clusters": sorted(canonical_micro_clusters),
        "latest_account_observed_at": latest.get("observed_at"),
        "account_snapshot_count": len(account_snapshots),
        "daily_notional_context_complete": daily_notional_complete,
        "daily_new_notional_basis": "broker_entry_orders_only",
        "protective_exit_orders_excluded_from_new_notional": True,
        "derived_position_classification_count": derived_position_classification_count,
        "position_classification_complete": _exposure_totals(
            {"positions": positions}
        )["unclassified_position_count"]
        == 0,
        "generated_at": generated_at,
    }


def _simulate_portfolio_lane(
    records: list[dict[str, Any]],
    *,
    lane: str,
    policy: dict[str, Any],
    initial_equity: float,
    generated_at: str,
) -> dict[str, Any]:
    eligible: list[tuple[str, float, str]] = []
    excluded_reason_counts: Counter[str] = Counter()
    for record in records:
        if lane == "historical":
            if record.get("replay_is_result_level_diagnostic_not_portfolio_simulation") is True:
                excluded_reason_counts["aggregate_result_not_chronological_trade_tape"] += 1
                continue
            if record.get("portfolio_simulation_eligible") is not True:
                excluded_reason_counts["historical_record_not_portfolio_simulation_eligible"] += 1
                continue
            outcome = record.get("outcome") if isinstance(record.get("outcome"), dict) else {}
            net_return = outcome.get("net_return")
            observed_at = record.get("outcome_available_at")
            identity = str(record.get("replay_id") or "")
        else:
            if record.get("simulated_elapsed_time") is not False:
                excluded_reason_counts["shadow_outcome_not_real_elapsed"] += 1
                continue
            net_return = record.get("net_return")
            observed_at = record.get("outcome_available_at")
            identity = str(record.get("outcome_id") or "")
        if net_return is None or parse_timestamp(observed_at) is None or not identity:
            excluded_reason_counts["record_missing_return_time_or_identity"] += 1
            continue
        eligible.append((str(observed_at), safe_float(net_return), identity))
    eligible.sort(key=lambda item: (item[0], item[2]))
    equity = initial_equity
    peak = initial_equity
    max_drawdown = 0.0
    total_pnl = 0.0
    for _observed_at, net_return, _identity in eligible:
        allocation = min(
            safe_float(policy["risk_budget"]["max_position_notional_usd"]),
            equity * safe_float(policy["risk_budget"]["max_instrument_notional_pct_equity"]),
        )
        pnl = allocation * net_return
        equity += pnl
        total_pnl += pnl
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, (peak - equity) / peak if peak > 0 else 0.0)
    return {
        "lane": lane,
        "generated_at": generated_at,
        "status": "measured_research_only" if eligible else "not_measurable_no_eligible_tape",
        "input_record_count": len(records),
        "eligible_record_count": len(eligible),
        "excluded_record_count": len(records) - len(eligible),
        "excluded_reason_counts": dict(sorted(excluded_reason_counts.items())),
        "initial_equity": initial_equity,
        "ending_equity": round(equity, 10),
        "total_pnl": round(total_pnl, 10),
        "portfolio_return": round((equity / initial_equity) - 1.0, 10)
        if initial_equity > 0
        else None,
        "maximum_drawdown": round(max_drawdown, 10),
        "fixed_policy_applied": POLICY_VERSION,
        "simulation_is_research_evidence_only": True,
        "paper_order_created": False,
        "proof_eligible": False,
    }


def _stress_test(
    portfolio: dict[str, Any],
    policy: dict[str, Any],
    generated_at: str,
    *,
    historical_replays: list[dict[str, Any]],
    shadow_outcomes: list[dict[str, Any]],
) -> dict[str, Any]:
    exposures = _exposure_totals(portfolio)
    gross = safe_float(exposures["gross_notional"])
    cluster_tail_loss = _estimated_tail_loss(portfolio, policy)
    scenarios = [
        ("broad_risk_off", 0.10 * gross),
        ("cluster_specific_tail", cluster_tail_loss),
        ("liquidity_spread_shock", 0.05 * gross),
        ("correlation_to_one", 0.15 * gross),
    ]
    rows = [
        {
            "scenario": name,
            "estimated_loss": round(loss, 10),
        }
        for name, loss in scenarios
    ]
    equity = safe_float(portfolio.get("equity"), 0.0)
    worst_loss = max((row["estimated_loss"] for row in rows), default=0.0)
    tail_budget = equity * safe_float(
        policy["risk_budget"]["max_tail_stress_loss_pct_equity"]
    )
    initial_equity = equity if equity > 0 else INITIAL_PAPER_BUDGET_USD
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_portfolio_stress_test",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": "no_open_positions" if gross == 0 else "research_stress_measured",
        "policy_version": policy["policy_version"],
        "gross_notional": gross,
        "scenarios": rows,
        "worst_estimated_loss": worst_loss,
        "worst_estimated_loss_pct_equity": round(worst_loss / equity, 10)
        if equity > 0
        else None,
        "tail_stress_budget": round(tail_budget, 10),
        "tail_stress_gate_passed": equity > 0 and worst_loss <= tail_budget,
        "historical_portfolio_simulation": _simulate_portfolio_lane(
            historical_replays,
            lane="historical",
            policy=policy,
            initial_equity=initial_equity,
            generated_at=generated_at,
        ),
        "forward_shadow_portfolio_simulation": _simulate_portfolio_lane(
            shadow_outcomes,
            lane="forward_shadow",
            policy=policy,
            initial_equity=initial_equity,
            generated_at=generated_at,
        ),
        "stress_test_is_not_forecast": True,
        "risk_approval_created": False,
        "authority": authority_flags(),
    }


def _nested_dicts(value: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if isinstance(value, dict):
        rows.append(value)
        for nested in value.values():
            rows.extend(_nested_dicts(nested))
    elif isinstance(value, list):
        for nested in value:
            rows.extend(_nested_dicts(nested))
    return rows


def _first_positive(records: list[dict[str, Any]], fields: tuple[str, ...]) -> float | None:
    for record in records:
        for field in fields:
            if record.get(field) is None:
                continue
            value = safe_float(record.get(field), -1.0)
            if value > 0:
                return value
    return None


def _evidence_record(akber_input: dict[str, Any], field: str) -> dict[str, Any]:
    evidence = akber_input.get("evidence")
    evidence = evidence if isinstance(evidence, dict) else {}
    record = evidence.get(field)
    return record if isinstance(record, dict) else {}


def _market_context_fresh(
    akber_input: dict[str, Any], *, generated_at: str, policy: dict[str, Any]
) -> tuple[bool, float | None]:
    observed = parse_timestamp(akber_input.get("generated_at"))
    generated = parse_timestamp(generated_at)
    if observed is None or generated is None:
        return False, None
    age = (generated - observed).total_seconds()
    maximum = safe_float(policy["market_quality"]["maximum_market_context_age_seconds"])
    fresh = bool(
        0 <= age <= maximum
        and akber_input.get("context_complete") is True
        and int(akber_input.get("fixture_or_sample_evidence_count") or 0) == 0
        and int(akber_input.get("stale_evidence_count") or 0) == 0
        and int(akber_input.get("incomplete_provenance_count") or 0) == 0
    )
    return fresh, age


def _market_family(trading_universe: dict[str, Any], symbol: str) -> str | None:
    for record in trading_universe.get("instruments", []):
        if isinstance(record, dict) and str(record.get("symbol") or "") == symbol:
            value = record.get("market_family")
            return str(value) if value else None
    return None


def _setup_from_lineage(
    hypothesis: dict[str, Any],
    edge: dict[str, Any],
    akber_input: dict[str, Any],
    akber_result: dict[str, Any],
    shadow_decisions: list[dict[str, Any]],
    shadow_outcomes: list[dict[str, Any]],
    shadow_promotion: dict[str, Any],
    trading_universe: dict[str, Any],
    policy: dict[str, Any],
    *,
    generated_at: str,
) -> dict[str, Any]:
    hypothesis_id = str(hypothesis.get("hypothesis_id") or "")
    evidence_class = str(
        hypothesis.get("evidence_class") or VALIDATED_PAPER_STRATEGY
    )
    tier = experimental_tier(hypothesis)
    instrument = str(
        hypothesis.get("instrument_proxy_mapping", {}).get("execution_proxy") or ""
    )
    confidence_class = (
        DISCOVERY_MICRO_CONFIDENCE_CLASS
        if evidence_class == EXPERIMENTAL_UNVALIDATED
        and tier == DISCOVERY_MICRO_TIER
        else EXPERIMENTAL_UNVALIDATED
        if evidence_class == EXPERIMENTAL_UNVALIDATED
        else str(
            edge.get("promotion_class")
            or hypothesis.get("edge_lineage", {}).get("promotion_class")
            or ""
        )
    )
    confidence_policy = policy.get("confidence_classes", {}).get(confidence_class, {})
    source_concentration = edge.get("source_concentration")
    source_concentration = (
        source_concentration if isinstance(source_concentration, dict) else {}
    )
    ratios = source_concentration.get("selected_trade_ratios")
    ratios = ratios if isinstance(ratios, dict) else {}
    source_families = sorted(str(key) for key in ratios if key)
    maximum_source_ratio = source_concentration.get("maximum_selected_trade_ratio")
    if evidence_class == EXPERIMENTAL_UNVALIDATED:
        pattern_lineage = hypothesis.get("pattern_lineage", {})
        source_families = sorted(
            str(value)
            for value in (
                akber_input.get("current_trigger_sources", [])
                if tier == DISCOVERY_MICRO_TIER
                else pattern_lineage.get("fresh_quorum_sources", [])
            )
            if str(value)
        )
        if tier == DISCOVERY_MICRO_TIER and all(
            safe_float(
                pattern_lineage.get("independent_market_confirmation", {}).get(field)
            )
            >= 1.0
            for field in (
                "current_market_price",
                "volatility_context",
            )
        ) and (
            akber_input.get("confirmation_alternative_satisfied") is True
        ):
            source_families.append("independent_live_market_confirmation")
            source_families = sorted(set(source_families))
        maximum_source_ratio = (
            round(1.0 / len(source_families), 6) if source_families else None
        )
    price_records = _nested_dicts(
        [
            _evidence_record(akber_input, "technical_confirmation").get("value"),
            _evidence_record(akber_input, "volume_or_flow_confirmation").get("value"),
            _evidence_record(akber_input, "volatility_context").get("value"),
        ]
    )
    liquidity_record = _evidence_record(akber_input, "liquidity_and_spread")
    liquidity_records = _nested_dicts(
        [liquidity_record.get("details"), liquidity_record.get("value")]
    )
    invalidation_record = _evidence_record(akber_input, "invalidation_clarity")
    invalidation_records = _nested_dicts(
        [invalidation_record.get("details"), invalidation_record.get("value")]
    )
    paperability = _evidence_record(akber_input, "paperability_proxy")
    paperability_details = (
        paperability.get("details") if isinstance(paperability.get("details"), dict) else {}
    )
    context_fresh, context_age = _market_context_fresh(
        akber_input, generated_at=generated_at, policy=policy
    )
    matching_decisions = [
        record
        for record in shadow_decisions
        if record.get("hypothesis_id") == hypothesis_id
    ]
    matching_outcomes = [
        record
        for record in shadow_outcomes
        if record.get("hypothesis_id") == hypothesis_id
        and record.get("simulated_elapsed_time") is False
    ]
    decision_time_shadow = matching_decisions[-1] if matching_decisions else {}
    invalidation_price = _first_positive(invalidation_records, ("invalidation_price",))
    max_loss_per_unit = _first_positive(invalidation_records, ("max_loss_per_unit",))
    invalidation = (
        {
            "invalidation_price": invalidation_price,
            "max_loss_per_unit": max_loss_per_unit,
            "source": "akber_v3_typed_invalidation_context",
        }
        if invalidation_price is not None or max_loss_per_unit is not None
        else None
    )
    spread_bps = _first_positive(liquidity_records, ("spread_bps",))
    average_daily_dollar_volume = _first_positive(
        liquidity_records + price_records,
        ("average_daily_dollar_volume", "average_daily_notional_20d"),
    )
    liquidity = (
        {
            "spread_bps": spread_bps,
            "average_daily_dollar_volume": average_daily_dollar_volume,
            "source": "akber_v3_typed_liquidity_context",
        }
        if spread_bps is not None or average_daily_dollar_volume is not None
        else None
    )
    risk_concept = (
        hypothesis.get("risk_concept")
        if isinstance(hypothesis.get("risk_concept"), dict)
        else {}
    )
    correlations = risk_concept.get("correlation_to_existing")
    correlations = correlations if isinstance(correlations, list) else []
    return {
        "setup_id": stable_id("risk-setup-v3", hypothesis_id),
        "hypothesis_id": hypothesis_id,
        "evidence_class": evidence_class,
        "experimental_tier": tier,
        "edge_id": hypothesis.get("edge_lineage", {}).get("edge_id"),
        "pattern_relationship_id": hypothesis.get("pattern_lineage", {}).get(
            "pattern_relationship_id"
        ),
        "score_id": hypothesis.get("pattern_lineage", {}).get("score_id"),
        "research_score": hypothesis.get("pattern_lineage", {}).get(
            "raw_research_score"
        ),
        "akber_result_id": akber_result.get("akber_result_id"),
        "research_goal_id": hypothesis.get("research_goal_lineage", {}).get(
            "research_goal_id"
        ),
        "instrument": instrument,
        "strategy_family_id": hypothesis.get("strategy_mapping", {}).get(
            "strategy_family_id"
        ),
        "correlated_cluster": _market_family(trading_universe, instrument),
        "direction": hypothesis.get("direction_horizon", {}).get("direction"),
        "expected_net_return": hypothesis.get("expected_edge_range", {}).get(
            "net_expectancy"
        ),
        "annualized_volatility": _first_positive(
            price_records,
            ("annualized_volatility", "rolling_volatility_20d_annualized"),
        ),
        "current_price": _first_positive(
            price_records,
            ("current_price", "last_price", "last_close", "price", "close"),
        ),
        "invalidation": invalidation,
        "liquidity": liquidity,
        "paperable": bool(
            paperability.get("available") is True
            and paperability_details.get("paperable") is True
            and paperability_details.get("paper_route")
            == "guarded_alpaca_paper_via_paperops"
        ),
        "paper_route": paperability_details.get("paper_route"),
        "uncertainty": confidence_policy.get("uncertainty_haircut"),
        "edge_confidence_class": confidence_class,
        "source_concentration": maximum_source_ratio,
        "source_families": source_families,
        "correlation_to_existing": correlations,
        "market_context_fresh": context_fresh,
        "market_context_age_seconds": context_age,
        "akber_decision": akber_result.get("decision"),
        "shadow_promotion_ready": bool(
            shadow_promotion.get("promotion_ready") is True and matching_outcomes
        ),
        "decision_time_shadow_snapshot_ready": bool(decision_time_shadow),
        "shadow_evidence_id": (
            decision_time_shadow.get("shadow_decision_id")
            or decision_time_shadow.get("decision_id")
            or decision_time_shadow.get("shadow_id")
        ),
        "shadow_decision_count": len(matching_decisions),
        "shadow_outcome_count": len(matching_outcomes),
        "quantity_increment": safe_float(
            paperability_details.get("quantity_increment"),
            safe_float(policy["rounding"]["default_quantity_increment"]),
        ),
        "proposal_only": True,
        "risk_approval_created": False,
        "execution_approval_created": False,
        "paper_order_created": False,
    }


def _apply_discovery_micro_cycle_capacity(
    proposals: list[dict[str, Any]],
    rejections: list[dict[str, Any]],
    portfolio: dict[str, Any],
    policy: dict[str, Any],
    *,
    generated_at: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Reserve bounded, cluster-distinct slots for the strongest setups."""

    micro = [
        proposal
        for proposal in proposals
        if proposal.get("experimental_tier") == DISCOVERY_MICRO_TIER
    ]
    maximum = int(
        policy.get("risk_budget", {}).get(
            "maximum_concurrent_discovery_micro_positions",
            MAXIMUM_CONCURRENT_DISCOVERY_POSITIONS,
        )
        or MAXIMUM_CONCURRENT_DISCOVERY_POSITIONS
    )
    available = max(
        maximum - int(portfolio.get("open_discovery_micro_exposure_count") or 0),
        0,
    )
    ranked = sorted(
        micro,
        key=lambda proposal: (
            -safe_float(proposal.get("expected_net_return")),
            -safe_float(proposal.get("research_score")),
            safe_float(proposal.get("spread_bps"), float("inf")),
            -safe_float(proposal.get("average_daily_dollar_volume")),
            str(proposal.get("instrument") or ""),
            str(proposal.get("proposal_id") or ""),
        ),
    )
    occupied_clusters = set(portfolio.get("open_discovery_micro_clusters") or [])
    retained_ids: set[str] = set()
    selected_clusters: set[str] = set()
    for proposal in ranked:
        cluster = str(proposal.get("correlated_cluster") or "unknown")
        if len(retained_ids) >= available:
            break
        if cluster in occupied_clusters or cluster in selected_clusters:
            continue
        retained_ids.add(str(proposal.get("proposal_id")))
        selected_clusters.add(cluster)
    retained = [
        proposal
        for proposal in proposals
        if proposal.get("experimental_tier") != DISCOVERY_MICRO_TIER
        or str(proposal.get("proposal_id")) in retained_ids
    ]
    for proposal in ranked:
        if str(proposal.get("proposal_id")) in retained_ids:
            continue
        cluster = str(proposal.get("correlated_cluster") or "unknown")
        rejection_reason = (
            "discovery_micro_correlated_cluster_slot_occupied"
            if cluster in occupied_clusters or cluster in selected_clusters
            else "discovery_micro_cycle_capacity_reserved_for_higher_ranked_setup"
        )
        rejections.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_risk_rejection",
                "phase_id": PHASE_ID,
                "generated_at": generated_at,
                "rejection_id": stable_id(
                    "risk-rejection-v3",
                    proposal.get("setup_id"),
                    rejection_reason,
                ),
                "setup_id": proposal.get("setup_id"),
                "hypothesis_id": proposal.get("hypothesis_id"),
                "evidence_class": proposal.get("evidence_class"),
                "experimental_tier": proposal.get("experimental_tier"),
                "edge_id": proposal.get("edge_id"),
                "pattern_relationship_id": proposal.get("pattern_relationship_id"),
                "score_id": proposal.get("score_id"),
                "rejection_reasons": [rejection_reason],
                "position_size_proposed": False,
                "risk_approval_created": False,
                "paper_order_created": False,
                "authority": authority_flags(),
            }
        )
    return retained, rejections


def build_portfolio_risk_engine_state(
    settings: Settings | None = None,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    generated = generated_at or now_iso()
    policy = default_portfolio_policy(generated)
    hypotheses = read_jsonl(runtime / HYPOTHESES_ARTIFACT)
    edges = read_jsonl(runtime / EDGE_REGISTRY_ARTIFACT)
    akber_inputs = read_jsonl(runtime / AKBER_INPUTS_ARTIFACT)
    akber_results = read_jsonl(runtime / AKBER_RESULTS_ARTIFACT)
    historical_replays = read_jsonl(runtime / AKBER_REPLAY_ARTIFACT)
    shadow_decisions = read_jsonl(runtime / SHADOW_DECISIONS_ARTIFACT)
    shadow_outcomes = read_jsonl(runtime / SHADOW_OUTCOMES_ARTIFACT)
    shadow = read_json(runtime / SHADOW_PROMOTION_ARTIFACT)
    portfolio_view = read_json(runtime / CURRENT_PORTFOLIO_ARTIFACT)
    trading_universe = read_json(runtime / TRADING_UNIVERSE_ARTIFACT)
    account_snapshots = read_jsonl(runtime / ACCOUNT_SNAPSHOTS_ARTIFACT)
    paper_orders = read_jsonl(runtime / PAPER_ORDERS_ARTIFACT)
    paperops = read_json(runtime / PAPEROPS_SUMMARY_ARTIFACT)
    portfolio = _current_portfolio_state(
        portfolio_view,
        account_snapshots,
        paper_orders,
        trading_universe,
        generated_at=generated,
    )
    edge_by_id = {
        str(record.get("edge_id")): record for record in edges if record.get("edge_id")
    }
    akber_input_by_id = {
        str(record.get("akber_input_id")): record
        for record in akber_inputs
        if record.get("akber_input_id")
    }
    akber_by_hypothesis = {
        str(record.get("hypothesis_id")): record
        for record in akber_results
        if record.get("hypothesis_id")
    }
    proposals: list[dict[str, Any]] = []
    rejections: list[dict[str, Any]] = []
    setup_contexts: list[dict[str, Any]] = []
    # Values are accepted only from typed current evidence. Narrative fields,
    # historical aggregates, and stale shadow entry prices are never used as
    # substitutes for current execution context.
    for hypothesis in hypotheses:
        hypothesis_id = str(hypothesis.get("hypothesis_id") or "")
        akber = akber_by_hypothesis.get(hypothesis_id, {})
        akber_input = akber_input_by_id.get(str(akber.get("akber_input_id")), {})
        edge_id = str(hypothesis.get("edge_lineage", {}).get("edge_id") or "")
        setup = _setup_from_lineage(
            hypothesis,
            edge_by_id.get(edge_id, {}),
            akber_input,
            akber,
            shadow_decisions,
            shadow_outcomes,
            shadow,
            trading_universe,
            policy,
            generated_at=generated,
        )
        setup_contexts.append(setup)
        result = evaluate_position_size(setup, portfolio, policy, generated_at=generated)
        if result["proposal"] is not None:
            proposals.append(result["proposal"])
        if result["rejection"] is not None:
            rejections.append(result["rejection"])

    proposals, rejections = _apply_discovery_micro_cycle_capacity(
        proposals,
        rejections,
        portfolio,
        policy,
        generated_at=generated,
    )

    exposures = _exposure_totals(portfolio)
    reason_counts = Counter(
        reason for record in rejections for reason in record.get("rejection_reasons", [])
    )
    stress = _stress_test(
        portfolio,
        policy,
        generated,
        historical_replays=historical_replays,
        shadow_outcomes=shadow_outcomes,
    )
    historical_simulation = stress["historical_portfolio_simulation"]
    forward_simulation = stress["forward_shadow_portfolio_simulation"]
    validated_proposals = [
        proposal
        for proposal in proposals
        if proposal.get("evidence_class") != EXPERIMENTAL_UNVALIDATED
    ]
    phase_acceptance_ready = bool(
        proposals
        and historical_simulation.get("status") == "measured_research_only"
        and stress.get("tail_stress_gate_passed") is True
        and (
            not validated_proposals
            or (
                shadow.get("promotion_ready") is True
                and forward_simulation.get("status") == "measured_research_only"
            )
        )
    )
    risk_state = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_portfolio_risk_state",
        "phase_id": PHASE_ID,
        "generated_at": generated,
        "status": (
            "risk_proposal_available"
            if proposals
            else "ready_no_eligible_setup"
            if not hypotheses
            else "fail_closed_context_required"
        ),
        "implementation_complete": True,
        "phase_acceptance_ready": phase_acceptance_ready,
        "policy_version": POLICY_VERSION,
        "portfolio_source_status": portfolio_view.get("status"),
        "portfolio_explicitly_empty": portfolio_view.get("explicitly_empty") is True,
        "portfolio_equity": portfolio.get("equity"),
        "position_count": len(_positions(portfolio)),
        "exposures": exposures,
        "daily_loss_pct": portfolio.get("daily_loss_pct"),
        "trailing_drawdown_pct": portfolio.get("trailing_drawdown_pct"),
        "new_notional_today": portfolio.get("new_notional_today"),
        "daily_new_notional_basis": portfolio.get("daily_new_notional_basis"),
        "open_order_count": portfolio.get("open_order_count"),
        "open_discovery_micro_exposure_count": portfolio.get(
            "open_discovery_micro_exposure_count"
        ),
        "open_discovery_micro_symbols": portfolio.get(
            "open_discovery_micro_symbols", []
        ),
        "open_discovery_micro_clusters": portfolio.get(
            "open_discovery_micro_clusters", []
        ),
        "derived_position_classification_count": portfolio.get(
            "derived_position_classification_count", 0
        ),
        "latest_account_observed_at": portfolio.get("latest_account_observed_at"),
        "account_snapshot_count": portfolio.get("account_snapshot_count"),
        "drawdown_context_complete": (
            portfolio.get("daily_loss_pct") is not None
            and portfolio.get("trailing_drawdown_pct") is not None
        ),
        "paperops_state": paperops.get("status"),
        "research_lock_active": paperops.get("status") == "watch_only_research_lock_active",
        "hypothesis_count": len(hypotheses),
        "experimental_hypothesis_count": sum(
            record.get("evidence_class") == EXPERIMENTAL_UNVALIDATED
            for record in hypotheses
        ),
        "experimental_proposal_count": sum(
            record.get("evidence_class") == EXPERIMENTAL_UNVALIDATED
            for record in proposals
        ),
        "discovery_micro_hypothesis_count": sum(
            record.get("evidence_class") == EXPERIMENTAL_UNVALIDATED
            and experimental_tier(record) == DISCOVERY_MICRO_TIER
            for record in hypotheses
        ),
        "discovery_micro_proposal_count": sum(
            record.get("evidence_class") == EXPERIMENTAL_UNVALIDATED
            and experimental_tier(record) == DISCOVERY_MICRO_TIER
            for record in proposals
        ),
        "typed_setup_context_count": len(setup_contexts),
        "proposal_count": len(proposals),
        "rejection_count": len(rejections),
        "rejection_reason_counts": dict(sorted(reason_counts.items())),
        "risk_approval_created_count": 0,
        "execution_approval_created_count": 0,
        "paper_order_created_count": 0,
        "historical_portfolio_simulation_status": historical_simulation.get("status"),
        "forward_shadow_portfolio_simulation_status": forward_simulation.get("status"),
        "absolute_trade_ceiling_usd": policy["risk_budget"][
            "max_position_notional_usd"
        ],
        "discovery_micro_trade_ceiling_usd": policy["risk_budget"][
            "discovery_micro_trade_ceiling_usd"
        ],
        "plain_english": (
            "No governed setup is available to size."
            if not hypotheses
            else "Sizing uses current evidence plus conservative broker-derived exposure context, while preserving every numeric risk limit and the guarded paper route."
        ),
        "authority": authority_flags(),
    }
    if proposals:
        risk_state["status"] = (
            "proposal_ready_for_router_review"
            if phase_acceptance_ready
            else "proposal_created_but_empirical_portfolio_evidence_maturing"
        )
    return {
        "policy": policy,
        "risk_state": risk_state,
        "proposals": proposals,
        "stress": stress,
        "rejections": rejections,
    }


def validate_portfolio_risk_engine_state(state: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    policy = state["policy"]
    risk_state = state["risk_state"]
    if policy.get("policy_version") != POLICY_VERSION:
        errors.append("portfolio_policy_version_invalid")
    capital = policy.get("capital_reference", {})
    risk_budget = policy.get("risk_budget", {})
    if safe_float(capital.get("initial_paper_budget_usd")) != INITIAL_PAPER_BUDGET_USD:
        errors.append("portfolio_initial_paper_budget_invalid")
    if not 0 < safe_float(risk_budget.get("max_position_notional_usd")) <= ABSOLUTE_TRADE_CEILING_USD:
        errors.append("portfolio_absolute_trade_ceiling_invalid")
    if safe_float(risk_budget.get("discovery_micro_trade_ceiling_usd")) != (
        DISCOVERY_MICRO_TRADE_CEILING_USD
    ):
        errors.append("portfolio_discovery_micro_trade_ceiling_invalid")
    if int(risk_budget.get("maximum_concurrent_discovery_micro_positions") or 0) != (
        MAXIMUM_CONCURRENT_DISCOVERY_POSITIONS
    ):
        errors.append("portfolio_discovery_micro_concurrency_invalid")
    if int(
        risk_budget.get("maximum_discovery_positions_per_correlated_cluster") or 0
    ) != MAXIMUM_DISCOVERY_POSITIONS_PER_CLUSTER:
        errors.append("portfolio_discovery_micro_cluster_limit_invalid")
    target = risk_budget.get("discovery_target_notional_usd", {})
    if (
        safe_float(target.get("minimum")) != DISCOVERY_TARGET_NOTIONAL_MIN_USD
        or safe_float(target.get("maximum")) != DISCOVERY_TARGET_NOTIONAL_MAX_USD
        or target.get("minimum_is_not_a_forced_floor") is not True
    ):
        errors.append("portfolio_discovery_target_range_invalid")
    change = policy.get("change_control", {})
    if change.get("human_governed") is not True:
        errors.append("portfolio_policy_not_human_governed")
    for field in (
        "automated_policy_changes_allowed",
        "llm_policy_changes_allowed",
        "quantum_policy_changes_allowed",
    ):
        if change.get(field) is not False:
            errors.append(f"portfolio_policy_unsafe_change_control:{field}")
    proposal_ids: set[str] = set()
    for proposal in state["proposals"]:
        proposal_id = str(proposal.get("proposal_id") or "")
        if not proposal_id or proposal_id in proposal_ids:
            errors.append("position_size_proposal_id_missing_or_duplicate")
        proposal_ids.add(proposal_id)
        if proposal.get("proposed_quantity", 0) <= 0:
            errors.append(f"position_size_not_positive:{proposal_id}")
        if proposal.get("maximum_loss_at_invalidation") is None:
            errors.append(f"position_size_invalidation_loss_missing:{proposal_id}")
        if proposal.get("quantity_rounded_down") is not True:
            errors.append(f"position_size_not_rounded_down:{proposal_id}")
        if proposal.get("proposal_only") is not True:
            errors.append(f"position_size_not_proposal_only:{proposal_id}")
        if safe_float(proposal.get("proposed_notional")) > safe_float(
            risk_budget.get("max_position_notional_usd")
        ) + 1e-8:
            errors.append(f"position_size_absolute_trade_ceiling_breached:{proposal_id}")
        limits = proposal.get("notional_limits")
        limits = limits if isinstance(limits, dict) else {}
        if not limits or any(
            safe_float(proposal.get("proposed_notional")) > safe_float(limit) + 1e-8
            for limit in limits.values()
        ):
            errors.append(f"position_size_notional_limit_breached:{proposal_id}")
        if safe_float(proposal.get("maximum_loss_at_invalidation")) > safe_float(
            proposal.get("risk_budget_dollars_after_uncertainty_haircut")
        ) + 1e-8:
            errors.append(f"position_size_invalidation_budget_breached:{proposal_id}")
        if not proposal.get("source_families"):
            errors.append(f"position_size_source_family_missing:{proposal_id}")
        if not proposal.get("edge_confidence_class"):
            errors.append(f"position_size_confidence_class_missing:{proposal_id}")
        if proposal.get("evidence_class") == EXPERIMENTAL_UNVALIDATED:
            if proposal.get("edge_id") or not (
                proposal.get("pattern_relationship_id")
                and proposal.get("score_id")
                and proposal.get("shadow_evidence_id")
            ):
                errors.append(
                    f"position_size_experimental_lineage_incomplete:{proposal_id}"
                )
            if experimental_tier(proposal) == DISCOVERY_MICRO_TIER and safe_float(
                proposal.get("proposed_notional")
            ) > DISCOVERY_MICRO_TRADE_CEILING_USD + 1e-8:
                errors.append(
                    f"position_size_discovery_micro_ceiling_breached:{proposal_id}"
                )
        if proposal.get("cross_position_correlation_context_complete") is not True:
            errors.append(f"position_size_correlation_context_incomplete:{proposal_id}")
        if proposal.get("paper_route") != "guarded_alpaca_paper_via_paperops":
            errors.append(f"position_size_unguarded_paper_route:{proposal_id}")
        for field in (
            "llm_size_input_used",
            "quantum_size_input_used",
            "risk_approval_created",
            "execution_approval_created",
            "paper_order_created",
        ):
            if proposal.get(field) is not False:
                errors.append(f"position_size_unsafe_field:{proposal_id}:{field}")
        errors.extend(validate_authority(proposal.get("authority", {}), prefix="risk_proposal"))
    for rejection in state["rejections"]:
        if not rejection.get("rejection_reasons"):
            errors.append("risk_rejection_reason_missing")
        if rejection.get("position_size_proposed") is not False:
            errors.append("risk_rejection_created_size")
        if rejection.get("risk_approval_created") is not False:
            errors.append("risk_rejection_created_approval")
        errors.extend(validate_authority(rejection.get("authority", {}), prefix="risk_rejection"))
    for field in (
        "risk_approval_created_count",
        "execution_approval_created_count",
        "paper_order_created_count",
    ):
        if risk_state.get(field) != 0:
            errors.append(f"portfolio_risk_forbidden_count_nonzero:{field}")
    if risk_state.get("portfolio_explicitly_empty") is True and risk_state.get(
        "position_count"
    ) != 0:
        errors.append("portfolio_empty_state_position_count_conflict")
    stress = state["stress"]
    for lane_name in (
        "historical_portfolio_simulation",
        "forward_shadow_portfolio_simulation",
    ):
        lane = stress.get(lane_name)
        if not isinstance(lane, dict):
            errors.append(f"portfolio_simulation_missing:{lane_name}")
            continue
        if lane.get("simulation_is_research_evidence_only") is not True:
            errors.append(f"portfolio_simulation_authority_boundary_missing:{lane_name}")
        if lane.get("paper_order_created") is not False:
            errors.append(f"portfolio_simulation_created_order:{lane_name}")
        if lane.get("proof_eligible") is not False:
            errors.append(f"portfolio_simulation_granted_proof:{lane_name}")
    if risk_state.get("phase_acceptance_ready") is True:
        if risk_state.get("proposal_count", 0) <= 0:
            errors.append("portfolio_phase_ready_without_size_proposal")
        if stress.get("historical_portfolio_simulation", {}).get("status") != (
            "measured_research_only"
        ):
            errors.append("portfolio_phase_ready_without_historical_simulation")
        validated_proposals = [
            proposal
            for proposal in state["proposals"]
            if proposal.get("evidence_class") != EXPERIMENTAL_UNVALIDATED
        ]
        if validated_proposals and stress.get(
            "forward_shadow_portfolio_simulation", {}
        ).get("status") != "measured_research_only":
            errors.append("portfolio_validated_phase_ready_without_forward_simulation")
    errors.extend(validate_authority(policy.get("authority", {}), prefix="portfolio_policy"))
    errors.extend(validate_authority(risk_state.get("authority", {}), prefix="portfolio_risk"))
    errors.extend(
        validate_authority(state["stress"].get("authority", {}), prefix="portfolio_stress")
    )
    return unique_errors(errors)


def build_and_write_portfolio_risk_engine(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    store = AtomicArtifactStore(runtime)
    state = build_portfolio_risk_engine_state(settings)
    store.write_json(POLICY_ARTIFACT, state["policy"])
    store.write_json(RISK_STATE_ARTIFACT, state["risk_state"])
    store.write_jsonl(PROPOSALS_ARTIFACT, state["proposals"])
    store.write_json(STRESS_TEST_ARTIFACT, state["stress"])
    store.write_jsonl(REJECTIONS_ARTIFACT, state["rejections"])
    errors = validate_portfolio_risk_engine_state(state)
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_portfolio_risk_engine_checks",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "implementation_ready": not errors,
        "implementation_complete": not errors,
        "phase_acceptance_ready": bool(
            not errors and state["risk_state"].get("phase_acceptance_ready") is True
        ),
        "policy_version": POLICY_VERSION,
        "portfolio_status": state["risk_state"]["status"],
        "position_count": state["risk_state"]["position_count"],
        "hypothesis_count": state["risk_state"]["hypothesis_count"],
        "proposal_count": len(state["proposals"]),
        "rejection_count": len(state["rejections"]),
        "absolute_trade_ceiling_usd": state["policy"]["risk_budget"][
            "max_position_notional_usd"
        ],
        "historical_portfolio_simulation_status": state["stress"][
            "historical_portfolio_simulation"
        ]["status"],
        "historical_portfolio_simulation_eligible_count": state["stress"][
            "historical_portfolio_simulation"
        ]["eligible_record_count"],
        "forward_shadow_portfolio_simulation_status": state["stress"][
            "forward_shadow_portfolio_simulation"
        ]["status"],
        "forward_shadow_portfolio_simulation_eligible_count": state["stress"][
            "forward_shadow_portfolio_simulation"
        ]["eligible_record_count"],
        "tail_stress_gate_passed": state["stress"]["tail_stress_gate_passed"],
        "risk_approval_created_count": 0,
        "execution_approval_created_count": 0,
        "paper_order_created_count": 0,
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "broker_write_count": 0,
        "authority": authority_flags(),
    }
    store.write_json(CHECK_ARTIFACT, checks)
    return state, checks, errors
