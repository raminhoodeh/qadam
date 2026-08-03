from __future__ import annotations

from copy import deepcopy

from orchestrator.qadam_experimental_paper_policy import default_policy
from orchestrator.qadam_operator_ready_common import authority_flags
from orchestrator.qadam_strategy_foundry_v3 import (
    build_strategy_foundry_v3_from_inputs,
    validate_strategy_foundry_v3_state,
)

NOW = "2026-07-18T08:00:00+00:00"


def _strategy(
    strategy_id: str = "strategy:test",
    *,
    evidence_class: str = "under_evidenced",
) -> dict:
    return {
        "strategy_family_id": strategy_id,
        "label": "Test Strategy",
        "evidence_class": evidence_class,
        "empirical_evidence": {
            "backtest_run_id": "backtest:test",
            "qadam_method_result_count": 12,
        },
        "failure_modes": [{"reason": "walk_forward_instability", "result_count": 3}],
        "next_evidence_requirement": "collect independent outcomes and rerun OR-8",
        "instrument_contribution": {
            "instruments": [
                {
                    "symbol": "TEST",
                    "paper_route_available": True,
                }
            ]
        },
    }


def _edge(*, promotion_class: str = "validated_research_edge") -> dict:
    return {
        "edge_id": "edge-v3:test",
        "promotion_class": promotion_class,
        "source_feature_definition": "independent source pressure leads TEST returns",
        "instrument": "TEST",
        "direction": "upside_under_confirmed_pressure",
        "horizon": "3d_forward",
        "regime": "risk_on",
        "score_version": "score:v3",
        "label_version": "label:v1",
        "backtest_run_id": "backtest:test",
        "fold_ids": ["fold-001"],
        "dataset_hashes": {"scores": "abc", "labels": "def"},
        "strategy_family_id": "strategy:test",
        "strategy_fit_vector": {"strategy:test": 0.8},
        "gross_expectancy": 0.02,
        "net_expectancy": 0.01,
        "confidence_distribution": {"lower": 0.001, "upper": 0.02},
        "decay_state": "current",
        "latest_supporting_sample": "2026-07-17T00:00:00+00:00",
        "falsifiers": ["relationship reverses"],
        "retirement_conditions": ["net expectancy turns non-positive"],
        "authority": authority_flags(),
    }


def _summary(edge_count: int) -> dict:
    return {
        "schema_version": "qadam_edge_registry.v2",
        "artifact_type": "qadam_edge_registry_summary",
        "generated_at": NOW,
        "status": (
            "edge_registry_complete_with_validated_edges"
            if edge_count
            else "edge_registry_complete_no_validated_edge"
        ),
        "implementation_complete": True,
        "edge_count": edge_count,
        "validated_edge_count": edge_count,
        "backtest_result_count": 360,
        "backtest_run_id": "backtest:test",
        "backtest_result_record_set_hash": "result-hash",
        "backtest_fold_record_set_hash": "fold-hash",
        "quantum_run_id": "quantum:test",
        "authority": authority_flags(),
    }


def _strategy_map(*strategies: dict) -> dict:
    rows = list(strategies) or [_strategy()]
    return {
        "schema_version": "qadam_edge_registry.v2",
        "artifact_type": "qadam_strategy_evidence_map_v3",
        "generated_at": NOW,
        "status": "strategy_map_complete",
        "strategy_count": len(rows),
        "strategies": rows,
        "authority": authority_flags(),
    }


def test_zero_edge_registry_is_a_valid_auditable_no_hypothesis_outcome() -> None:
    strategy_map = _strategy_map(
        _strategy(),
        _strategy("strategy:exploratory", evidence_class="exploratory"),
    )
    state = build_strategy_foundry_v3_from_inputs([], _summary(0), strategy_map, generated_at=NOW)

    assert validate_strategy_foundry_v3_state(state) == []
    assert state["primary"]["status"] == "foundry_complete_no_eligible_edges"
    assert state["primary"]["valid_no_hypothesis_outcome"] is True
    assert state["primary"]["hypothesis_count"] == 0
    assert state["primary"]["pattern_score_rows_consumed_count"] == 0
    assert state["primary"]["rejection_scope_counts"] == {"strategy_family_evidence_gate": 2}
    assert all(
        record["configured_strategy_is_not_an_edge"] is True for record in state["rejections"]
    )


def test_validated_edge_forms_one_akber_reviewable_research_hypothesis() -> None:
    state = build_strategy_foundry_v3_from_inputs(
        [_edge()], _summary(1), _strategy_map(_strategy()), generated_at=NOW
    )

    assert validate_strategy_foundry_v3_state(state) == []
    assert state["primary"]["hypothesis_count"] == 1
    hypothesis = state["hypotheses"][0]
    assert hypothesis["hypothesis_state"] == "ready_for_akber_review"
    assert hypothesis["akber_review_allowed"] is True
    assert hypothesis["edge_lineage"]["edge_registry_reference"]["complete"] is True
    assert hypothesis["candidate_identity_material"]["trade_candidate_created"] is False
    assert hypothesis["paper_order_created"] is False


def test_exploratory_edge_is_confined_to_shadow_only() -> None:
    edge = _edge(promotion_class="exploratory_research_edge")
    summary = _summary(1)
    summary["validated_edge_count"] = 0
    state = build_strategy_foundry_v3_from_inputs(
        [edge], summary, _strategy_map(_strategy()), generated_at=NOW
    )

    assert validate_strategy_foundry_v3_state(state) == []
    hypothesis = state["hypotheses"][0]
    assert hypothesis["hypothesis_state"] == "shadow_only"
    assert hypothesis["akber_review_allowed"] is False
    assert hypothesis["blocker_state"]["router_eligible"] is False


def test_non_positive_edge_is_rejected_before_akber() -> None:
    edge = _edge()
    edge["net_expectancy"] = 0.0
    state = build_strategy_foundry_v3_from_inputs(
        [edge], _summary(1), _strategy_map(_strategy()), generated_at=NOW
    )

    assert validate_strategy_foundry_v3_state(state) == []
    assert state["hypotheses"] == []
    assert state["rejections"][0]["rejection_scope"] == "edge_record"
    assert "non_positive_expected_return_after_costs" in state["rejections"][0]["rejection_reasons"]


def test_duplicate_or10_edge_ids_fail_closed() -> None:
    duplicate = deepcopy(_edge())
    state = build_strategy_foundry_v3_from_inputs(
        [_edge(), duplicate], _summary(2), _strategy_map(_strategy()), generated_at=NOW
    )

    errors = validate_strategy_foundry_v3_state(state)
    assert state["primary"]["status"] == "foundry_blocked_invalid_or10_input"
    assert state["hypotheses"] == []
    assert any("or10_edge_id_missing_or_duplicate" in error for error in errors)


def test_incomplete_or10_lineage_fails_closed() -> None:
    summary = _summary(0)
    summary["backtest_result_record_set_hash"] = None
    state = build_strategy_foundry_v3_from_inputs(
        [], summary, _strategy_map(_strategy()), generated_at=NOW
    )

    errors = validate_strategy_foundry_v3_state(state)
    assert state["primary"]["implementation_complete"] is False
    assert state["hypotheses"] == []
    assert any("or10_backtest_result_hash_missing" in error for error in errors)


def test_complete_current_pattern_forms_unvalidated_experimental_hypothesis() -> None:
    strategy = _strategy(evidence_class="under_evidenced")
    strategy["best_observed_rejected_result"] = {
        "mean_gross_return": 0.02,
        "mean_net_return": 0.01,
        "not_a_validated_expectancy": True,
        "rejection_reasons": ["false_discovery_adjusted_result_not_significant"],
    }
    score = {
        "score_id": "pattern-score-v3:test",
        "feature_vector_id": "feature-vector-v3:test",
        "input_fingerprint": "fingerprint:test",
        "model_version": "pattern_score_v3:test",
        "raw_pattern_score": 0.65,
        "confidence_state": "score_ready_for_tape",
        "negative_control": False,
        "missing_critical_features": [],
        "direction_hypothesis": "upside_under_confirmed_pressure",
        "horizon_hypothesis": "3d_forward",
        "instrument": "TEST",
        "market_family": "test",
        "strategy_family_id": "strategy:test",
        "strategy_agnostic": False,
        "features": {"strategy_fit": 1.0},
        "expected_reward_to_risk": 1.8,
        "feature_inputs": [
            {
                "source_key": "source-a",
                "fresh": True,
                "quorum_eligible": True,
                "independence_cluster_id": "cluster-a",
            },
            {
                "source_key": "source-b",
                "fresh": True,
                "quorum_eligible": True,
                "independence_cluster_id": "cluster-b",
            },
        ],
        "scoring_as_of": NOW,
    }
    policy = default_policy(NOW)

    state = build_strategy_foundry_v3_from_inputs(
        [],
        _summary(0),
        _strategy_map(strategy),
        generated_at=NOW,
        pattern_scores=[score],
        experimental_policy=policy,
    )

    assert validate_strategy_foundry_v3_state(state) == []
    assert state["primary"]["experimental_hypothesis_count"] == 1
    hypothesis = state["hypotheses"][0]
    assert hypothesis["evidence_class"] == "experimental_unvalidated"
    assert hypothesis["edge_lineage"]["edge_id"] is None
    assert hypothesis["pattern_lineage"]["pattern_relationship_id"]
    assert hypothesis["akber_review_allowed"] is True
    assert hypothesis["risk_concept"]["expected_reward_to_risk"] == 1.8


def test_non_quorum_source_cannot_form_discovery_micro_hypothesis() -> None:
    strategy = _strategy(evidence_class="under_evidenced")
    strategy["best_observed_rejected_result"] = {
        "mean_gross_return": 0.02,
        "mean_net_return": 0.01,
        "not_a_validated_expectancy": True,
        "rejection_reasons": ["walk_forward_instability"],
    }
    score = {
        "score_id": "pattern-score-v3:micro",
        "feature_vector_id": "feature-vector-v3:micro",
        "input_fingerprint": "fingerprint:micro",
        "model_version": "pattern_score_v3:test",
        "raw_pattern_score": 0.47,
        "confidence_state": "blocked_missing_critical_features",
        "negative_control": False,
        "missing_critical_features": ["fresh_source_quorum"],
        "direction_hypothesis": "upside_under_confirmed_pressure",
        "horizon_hypothesis": "3d_forward",
        "instrument": "TEST",
        "market_family": "test",
        "strategy_family_id": "strategy:test",
        "strategy_agnostic": False,
        "features": {
            "strategy_fit": 1.0,
            "current_market_price": 1.0,
            "volatility_context": 1.0,
            "volume_or_flow_context": 1.0,
        },
        "feature_inputs": [
            {
                "source_key": "source-a",
                "fresh": True,
                "quorum_eligible": False,
                "mapping_class": "causal_strategy_mapping",
                "trust_score": 0.80,
                "independence_cluster_id": "cluster-a",
                "provenance": ["provider:test"],
            }
        ],
        "scoring_as_of": NOW,
    }

    state = build_strategy_foundry_v3_from_inputs(
        [],
        _summary(0),
        _strategy_map(strategy),
        generated_at=NOW,
        pattern_scores=[score],
        experimental_policy=default_policy(NOW),
    )

    assert validate_strategy_foundry_v3_state(state) == []
    assert state["primary"]["discovery_micro_hypothesis_count"] == 0
    assert state["hypotheses"] == []
    assert any(
        "discovery_micro_fresh_catalyst_not_met" in row["rejection_reasons"]
        for row in state["rejections"]
    )


def _micro_score(symbol: str, *, direction: str = "upside_under_confirmed_pressure") -> dict:
    return {
        "score_id": f"pattern-score-v3:{symbol.lower()}",
        "feature_vector_id": f"feature-vector-v3:{symbol.lower()}",
        "input_fingerprint": f"fingerprint:{symbol.lower()}",
        "model_version": "pattern_score_v3:test",
        "raw_pattern_score": 0.65,
        "confidence_state": "score_ready_for_tape",
        "negative_control": False,
        "missing_critical_features": [],
        "direction_hypothesis": direction,
        "horizon_hypothesis": "3d_forward",
        "instrument": symbol,
        "market_family": "test",
        "strategy_family_id": "strategy:test",
        "strategy_agnostic": False,
        "features": {
            "strategy_fit": 1.0,
            "current_market_price": 1.0,
            "volatility_context": 1.0,
            "volume_or_flow_context": 1.0,
        },
        "feature_inputs": [
            {
                "source_key": "source-a",
                "fresh": True,
                "quorum_eligible": True,
                "mapping_class": "causal_strategy_mapping",
                "trust_score": 0.80,
                "independence_cluster_id": "cluster-a",
                "provenance": ["provider:test"],
            },
            {
                "source_key": "source-b",
                "fresh": True,
                "quorum_eligible": True,
                "mapping_class": "causal_strategy_mapping",
                "trust_score": 0.82,
                "independence_cluster_id": "cluster-b",
                "provenance": ["provider:test"],
            },
        ],
        "scoring_as_of": NOW,
    }


def test_pattern_that_fits_both_tiers_prefers_smaller_discovery_micro() -> None:
    strategy = _strategy(evidence_class="under_evidenced")
    strategy["best_observed_rejected_result"] = {
        "instrument": "TEST",
        "mean_gross_return": 0.02,
        "mean_net_return": 0.01,
        "not_a_validated_expectancy": True,
    }
    state = build_strategy_foundry_v3_from_inputs(
        [],
        _summary(0),
        _strategy_map(strategy),
        generated_at=NOW,
        pattern_scores=[_micro_score("TEST")],
        experimental_policy=default_policy(NOW),
    )

    assert validate_strategy_foundry_v3_state(state) == []
    hypothesis = state["hypotheses"][0]
    assert hypothesis["experimental_tier"] == "discovery_micro"
    assert hypothesis["direction_horizon"]["direction"] == "long"
    assert (
        hypothesis["direction_horizon"]["research_direction_hypothesis"]
        == "upside_under_confirmed_pressure"
    )


def test_ambiguous_direction_is_rejected_before_akber() -> None:
    state = build_strategy_foundry_v3_from_inputs(
        [],
        _summary(0),
        _strategy_map(_strategy(evidence_class="under_evidenced")),
        generated_at=NOW,
        pattern_scores=[_micro_score("TEST", direction="conditional_asymmetry")],
        experimental_policy=default_policy(NOW),
    )

    assert state["hypotheses"] == []
    assert any(
        "direction_not_actionable" in row["rejection_reasons"]
        for row in state["rejections"]
    )


def test_duplicate_instrument_variants_select_historically_best_proxy() -> None:
    strategy = _strategy(evidence_class="under_evidenced")
    strategy["instrument_contribution"]["instruments"] = [
        {"symbol": "BNO", "paper_route_available": True},
        {"symbol": "USO", "paper_route_available": True},
        {"symbol": "XLE", "paper_route_available": True},
    ]
    strategy["best_observed_rejected_result"] = {
        "instrument": "USO",
        "mean_gross_return": 0.02,
        "mean_net_return": 0.01,
        "not_a_validated_expectancy": True,
    }
    scores = [_micro_score(symbol) for symbol in ("BNO", "USO", "XLE")]
    state = build_strategy_foundry_v3_from_inputs(
        [],
        _summary(0),
        _strategy_map(strategy),
        generated_at=NOW,
        pattern_scores=scores,
        experimental_policy=default_policy(NOW),
    )

    assert validate_strategy_foundry_v3_state(state) == []
    assert len(state["hypotheses"]) == 1
    assert state["hypotheses"][0]["instrument_proxy_mapping"]["execution_proxy"] == "USO"
    assert sum(
        "redundant_instrument_variant_not_selected" in row["rejection_reasons"]
        for row in state["rejections"]
    ) == 2
