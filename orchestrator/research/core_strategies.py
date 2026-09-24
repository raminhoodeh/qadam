"""Read model for the five enduring core families, not another trading owner."""

from collections import Counter

from orchestrator.qadam_wave_b_common import STRATEGY_HYPOTHESES


def build_core_strategy_status(state, *, scores, directions, source_coverage):
    rows = []
    coverage = {row["strategy_family_id"]: row for row in
                source_coverage.get("strategy_source_coverage", [])}
    for family, thesis in STRATEGY_HYPOTHESES.items():
        hypotheses = [row for row in state["hypotheses"]
                      if row.get("strategy_mapping", {}).get("strategy_family_id") == family]
        observations = [row for row in scores if row.get("strategy_family_id") == family
                        and not row.get("negative_control")]
        resolutions = [row for row in directions if row.get("strategy_family_id") == family
                       and not row.get("negative_control")]
        reasons = Counter(reason for row in state["rejections"]
                          if row.get("strategy_family_id") == family
                          for reason in row.get("rejection_reasons", []))
        directional = [row for row in resolutions if row.get("actionable_direction") in {"long", "short"}]
        rows.append({
            "strategy_family_id": family,
            "operating_model": "stable_core_rules_with_bounded_paper_observations",
            "state": "eligible_for_canonical_review" if hypotheses else
                     "waiting_for_usable_inputs" if not observations else
                     "waiting_for_directional_trigger" if not directional else "waiting_for_admission",
            "configured_horizon": thesis["horizon"],
            "research_direction_is_not_execution_direction": True,
            "research_observation_count": len(observations),
            "highest_research_score": max((row.get("raw_pattern_score", 0) for row in observations), default=None),
            "score_is_profit_probability": False,
            "resolved_signal_count": len(directional),
            "eligible_hypothesis_count": len(hypotheses),
            "current_strategy_version_ids": sorted({row["strategy_version_id"] for row in hypotheses}),
            "blockers": dict(sorted(reasons.items())),
            "latest_signal_explanations": sorted({row.get("explanation", "") for row in resolutions}),
            "source_coverage": coverage.get(family, {}),
            "rule_changes_require_new_version": True,
            "observation_refresh_requires_new_version": False,
            "completed_forward_outcomes_required_before_micro_paper_review": False,
            "execution_authority": "canonical_decision_then_portfolio_risk_router_single_paperops_owner",
        })
    return {
        "schema_version": "qadam_core_strategy_status.v1",
        "generated_at": state["primary"]["generated_at"],
        "core_family_count": len(rows), "core_families": rows,
        "validated_lane_input_errors": state["primary"].get("validated_lane_input_errors", []),
        "learning_contract": "immutable_registered_definition_matched_forward_vs_SPY_and_no_trade",
        "learning_rule": "Keep incumbent rules while outcomes mature; compare changed rules under a new version.",
        "paper_only": True, "broker_write_count": 0,
        "configured_core_family_is_not_a_validated_edge": True,
    }
