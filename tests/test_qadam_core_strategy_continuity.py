from copy import deepcopy

from orchestrator.qadam_experimental_paper_policy import default_policy
from orchestrator.research.core_strategies import build_core_strategy_status
from orchestrator.research.foundry import (
    build_experimental_strategy_hypothesis,
    build_strategy_foundry_v3_from_inputs,
    experimental_pattern_admission,
    validate_strategy_foundry_v3_state,
)
from tests.test_qadam_strategy_foundry_v3 import _micro_score, _strategy, _strategy_map, _summary, NOW


def hypothesis(score, policy=None):
    return build_experimental_strategy_hypothesis(
        score, _strategy(), generated_at=NOW, policy=policy or default_policy(NOW),
        score_lineage={"pattern_score_record_set_hash": "test"},
    )


def test_source_freshness_and_score_updates_do_not_restart_strategy_learning():
    score = _micro_score("TEST")
    score["feature_inputs"].append({
        **score["feature_inputs"][0], "source_key": "second", "independence_cluster_id": "second",
    })
    first = hypothesis(score)
    changed = deepcopy(score)
    changed["score_id"] = "a-new-observation"
    changed["feature_vector_id"] = "a-new-vector"
    changed["feature_inputs"][1]["fresh"] = False
    changed["raw_pattern_score"] = 0.7
    second = hypothesis(changed)
    assert first["strategy_version_id"] == second["strategy_version_id"]
    assert first["hypothesis_id"] != second["hypothesis_id"]
    assert first["pattern_lineage"]["fresh_support_sources"] != second["pattern_lineage"]["fresh_support_sources"]


def test_rule_and_source_universe_changes_create_distinct_versions():
    score = _micro_score("TEST")
    first = hypothesis(score)
    policy = default_policy(NOW)
    policy["discovery_micro_admission"]["minimum_research_score"] = 0.46
    assert first["strategy_version_id"] != hypothesis(score, policy)["strategy_version_id"]
    changed = deepcopy(score)
    changed["feature_inputs"][0]["source_key"] = "different-source-recipe"
    assert first["strategy_version_id"] != hypothesis(changed)["strategy_version_id"]


def test_missing_backtest_does_not_kill_complete_small_paper_signal():
    state = build_strategy_foundry_v3_from_inputs(
        [], {}, _strategy_map(), generated_at=NOW,
        pattern_scores=[_micro_score("TEST")], experimental_policy=default_policy(NOW),
    )
    assert validate_strategy_foundry_v3_state(state) == []
    assert len(state["hypotheses"]) == 1
    assert state["primary"]["validated_lane_input_errors"]
    row = state["hypotheses"][0]
    assert row["experimental_tier"] == "discovery_micro"
    assert row["edge_lineage"]["edge_id"] is None
    assert row["paper_order_created"] is False


def test_optional_volume_does_not_veto_discovery_but_required_market_data_does():
    score = _micro_score("TEST")
    score["features"]["volume_or_flow_context"] = 0.0
    score["missing_critical_features"] = ["volume_or_flow_context"]
    score["confidence_state"] = "blocked_missing_critical_features"
    policy = default_policy(NOW)
    admission = experimental_pattern_admission(score, _strategy(), policy)
    assert admission["admitted"] is True
    assert admission["tier"] == "discovery_micro"
    strict = deepcopy(policy)
    strict["discovery_micro_admission"]["volume_or_flow_required"] = True
    assert experimental_pattern_admission(score, _strategy(), strict)["admitted"] is False
    for feature in ["current_market_price", "volatility_context"]:
        missing = deepcopy(score)
        missing["features"][feature] = 0.0
        missing["missing_critical_features"].append(feature)
        assert experimental_pattern_admission(missing, _strategy(), policy)["admitted"] is False


def test_missing_direction_or_bad_mapping_still_blocks():
    for score, mapping in [(_micro_score("TEST", direction="unknown"), _strategy_map()),
                           (_micro_score("TEST"), {})]:
        state = build_strategy_foundry_v3_from_inputs(
            [], {}, mapping, generated_at=NOW,
            pattern_scores=[score], experimental_policy=default_policy(NOW),
        )
        assert state["hypotheses"] == []


def test_unavailable_bounded_variant_cannot_displace_complete_micro_signal():
    strategy = _strategy()
    strategy["instrument_contribution"]["instruments"].append({
        "symbol": "OTHER", "paper_route_available": True,
    })
    strategy["best_observed_rejected_result"] = {
        "instrument": "OTHER", "mean_net_return": 0.01, "not_a_validated_expectancy": True,
    }
    bounded = _micro_score("OTHER")
    for source in bounded["feature_inputs"]:
        source["trust_score"] = 0.4
    state = build_strategy_foundry_v3_from_inputs(
        [], {}, _strategy_map(strategy), generated_at=NOW,
        pattern_scores=[bounded, _micro_score("TEST")], experimental_policy=default_policy(NOW),
    )
    assert validate_strategy_foundry_v3_state(state) == []
    assert len(state["hypotheses"]) == 1
    assert state["hypotheses"][0]["instrument_proxy_mapping"]["execution_proxy"] == "TEST"
    assert state["hypotheses"][0]["experimental_tier"] == "discovery_micro"


def test_corrupt_historical_authority_is_not_reclassified_as_missing_history():
    summary = _summary(0)
    summary["authority"]["broker_write_allowed"] = True
    state = build_strategy_foundry_v3_from_inputs(
        [], summary, _strategy_map(), generated_at=NOW,
        pattern_scores=[_micro_score("TEST")], experimental_policy=default_policy(NOW),
    )
    assert state["hypotheses"] == []
    assert state["primary"]["input_validation_errors"]


def test_five_core_families_remain_visible_without_active_signals():
    state = build_strategy_foundry_v3_from_inputs([], _summary(0), _strategy_map(), generated_at=NOW)
    status = build_core_strategy_status(state, scores=[], directions=[], source_coverage={})
    assert status["core_family_count"] == 5
    assert all(row["state"] == "waiting_for_usable_inputs" for row in status["core_families"])
    assert status["configured_core_family_is_not_a_validated_edge"]
