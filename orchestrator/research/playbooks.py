"""Bounded feature contracts and capacity, not another admission authority."""

from orchestrator.qadam_wave_b_common import STRATEGY_HYPOTHESES

PREFERRED_FAMILIES = ("semiconductor_policy_options_asymmetry", "crude_oil_energy_security_disruption")


def playbook_definition(family):
    thesis = STRATEGY_HYPOTHESES.get(family, {})
    return {
        "version": "event-assisted-paper-playbook.1",
        "family": family,
        "horizon": thesis.get("horizon"),
        "horizon_basis": "elapsed_time_then_first_executable_session",
        "mandatory_features": {
            "causal_trigger": "typed_profile_specific_current_event_or_regime_producer",
            "direction": "deterministic_strategy_translation_not_research_score",
            "price": "provider_backed_executable_quote",
            "spread": "provider_bid_ask_measurement",
            "liquidity": "provider_volume_or_average_dollar_volume",
            "volatility": "provider_price_history_rolling_volatility",
            "invalidation": "frozen_strategy_exit_definition_then_numeric_risk_proposal",
        },
        "optional_features": ["frontier_model", "local_model", "quantum_comparison", "transcript"],
        "optional_feature_missing_is_global_veto": False,
        "comparators": ["matched_SPY", "no_trade", "preregistered_price_volatility_baseline"],
        "short_horizon_challenger": {
            "horizon": "2d_forward", "basis": "elapsed_time_not_two_market_sessions",
            "rationale": "Test whether event repricing decays before the incumbent horizon.",
            "state": "prospective_shadow_challenger_no_order_authority",
            "automatic_horizon_change_allowed": False,
        },
        "return_class_when_unestimated": "unestimated_discovery_experiment",
        "maximum_unestimated_notional_usd": 250.0,
        "maximum_unestimated_planned_loss_usd": 5.0,
        "paper_only": True,
    }


def horizon_challengers(hypotheses):
    from copy import deepcopy
    from orchestrator.qadam_strategy_definition import version_hypothesis
    from orchestrator.qadam_wave_b_common import stable_id
    results, represented = [], set()
    for original in hypotheses:
        family = original.get("strategy_mapping", {}).get("strategy_family_id")
        if family not in PREFERRED_FAMILIES or family in represented or not original.get("strategy_version_id"):
            continue
        if original.get("direction_horizon", {}).get("horizon") == "2d_forward":
            continue
        row = deepcopy(original)
        row.update(hypothesis_id=stable_id("horizon-challenger", original["hypothesis_id"], "2d_forward"),
                   hypothesis_state="shadow_only", research_role="two_day_event_decay_challenger",
                   comparison_parent_version_id=original["strategy_version_id"], akber_review_allowed=False)
        row["direction_horizon"]["horizon"] = "2d_forward"
        row["entry_concept"] = {**row.get("entry_concept", {}),
                                "research_only_comparison": "event_decay_2_elapsed_days_not_two_sessions"}
        results.append(version_hypothesis(row))
        represented.add(family)
    return results


def capacity_projection(*, average_holding_sessions=None, usable_clusters=3, concurrent_slots=3):
    slots = max(0, min(int(usable_clusters), int(concurrent_slots), 3))
    return {
        "usable_independent_slots": slots,
        "target_entries_per_five_sessions": [5, 10],
        "full_utilisation_entry_capacity": round(slots * 5 / average_holding_sessions, 2)
        if average_holding_sessions and average_holding_sessions > 0 else None,
        "average_holding_sessions": average_holding_sessions,
        "current_hold_duration_measured": average_holding_sessions is not None,
        "scenario_capacity_by_holding_sessions": {str(days): slots * 5 / days for days in (1, 2, 3, 5)},
        "opportunity_arrival_not_guaranteed": True,
        "capacity_is_not_permission_to_shorten_positions": True,
        "binding_limits": ["independent_triggers", "three_discovery_slots", "one_per_correlated_cluster", "holding_period"],
    }
