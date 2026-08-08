from __future__ import annotations

from copy import deepcopy

from orchestrator.qadam_akber_filter_v3 import (
    CONTEXT_FIELDS,
    assemble_current_akber_context,
    build_akber_filter_v3_from_inputs,
    build_akber_input,
    build_historical_akber_replay,
    build_stage_ablations,
    build_threshold_proposals,
    evaluate_akber_input,
    validate_akber_filter_v3_state,
)
from orchestrator.qadam_experimental_paper_policy import (
    DISCOVERY_MICRO_TIER,
    EVENT_CATALYST_PROFILE,
    EXPERIMENTAL_UNVALIDATED,
    REGIME_STATE_PROFILE,
)
from orchestrator.qadam_operator_ready_common import authority_flags

NOW = "2026-07-18T08:00:00+00:00"


def _hypothesis() -> dict:
    return {
        "generated_at": NOW,
        "hypothesis_id": "hypothesis:test",
        "hypothesis_state": "ready_for_akber_review",
        "akber_review_allowed": True,
        "edge_lineage": {
            "edge_id": "edge:test",
            "backtest_run_id": "backtest:test",
            "edge_registry_reference": {"complete": True},
            "applied_learning_version_ids": [],
        },
        "research_goal_lineage": {"research_goal_id": "goal:test"},
        "candidate_identity_material": {"candidate_identity_id": "identity:test"},
        "instrument_proxy_mapping": {
            "observed_instrument": "TEST",
            "execution_proxy": "TEST",
        },
        "direction_horizon": {"direction": "long", "horizon": "3d_forward"},
        "expected_edge_range": {
            "net_expectancy": 0.01,
            "confidence_distribution": {"lower": 0.001, "upper": 0.02},
        },
        "invalidation_exit": {"invalidation_conditions": ["relationship reverses"]},
        "risk_concept": {"expected_reward_to_risk": 2.0},
    }


def _micro_hypothesis() -> dict:
    hypothesis = _hypothesis()
    hypothesis.update(
        {
            "evidence_class": EXPERIMENTAL_UNVALIDATED,
            "experimental_tier": DISCOVERY_MICRO_TIER,
            "edge_lineage": {
                "edge_id": None,
                "edge_registry_reference": {"complete": False},
                "applied_learning_version_ids": [],
            },
            "pattern_lineage": {
                "complete": True,
                "pattern_relationship_id": "pattern:micro",
                "score_id": "score:micro",
                "source_confirmation_mode": (
                    "profile_specific_current_trigger_plus_one_live_market_confirmation"
                ),
                "evidence_profile": EVENT_CATALYST_PROFILE,
                "fresh_support_sources": ["source-a"],
                "fresh_trigger_sources": [],
                "provider_availability_is_not_trigger": True,
            },
            "strategy_mapping": {"strategy_family_id": "strategy:test"},
            "expected_edge_range": {
                "net_expectancy": 0.0025,
                "not_a_validated_expectancy": True,
                "confidence_distribution": {"lower": None, "upper": None},
            },
            "risk_concept": {"expected_reward_to_risk": 1.5},
        }
    )
    return hypothesis


def _current_artifacts(*, technical_state: str = "ok") -> dict:
    return {
        "market_context": {
            "recent_packets": [
                {
                    "packet_id": "packet:test",
                    "generated_at": NOW,
                    "research_goal_origin": "live_source",
                    "market_context_status": "context_ready",
                    "watched_instruments": ["TEST"],
                    "source_taxonomy": [
                        {
                            "source_key": "source-a",
                            "observed_in_goal": True,
                            "required_for_goal": True,
                            "status": "ok",
                            "trust_score": 0.8,
                        }
                    ],
                    "source_quorum_result": {"status": "pass", "score": 1.0},
                    "hypothesis": "A fresh test catalyst is corroborated.",
                    "missing_context": [],
                    "price_volume_context": {
                        "status": "ok",
                        "provider": "alpaca_market_data_v2",
                        "records": [
                            {
                                "symbol": "TEST",
                                "last_close": 100.0,
                                "market_state": "live",
                                "volume_ratio": 1.5,
                                "rolling_volatility_20d": 0.02,
                                "spread_bps": 8.0,
                                "average_daily_dollar_volume": 10_000_000.0,
                            }
                        ],
                    },
                    "technical_context": {
                        "status": technical_state,
                        "records": [
                            {
                                "symbol": "TEST",
                                "setup_type": "trend_confirmation",
                            }
                        ],
                    },
                    "orderflow_context": {"status": "unavailable", "records": []},
                }
            ]
        },
        "signal_integrity_reviews": [
            {
                "review_id": "review:test",
                "reviewed_at": NOW,
                "instrument_focus": "TEST",
                "market_confirmation_policy": {
                    "pricing_gap_result": "measured_small_discount",
                    "pricing_gap_status": "measured",
                },
            }
        ],
        "alpaca_mirror": {
            "status": "ok",
            "write_authority": False,
            "snapshot": {
                "mode": "paper",
                "connection_status": "alpaca_paper_readonly_connected",
                "observed_at": NOW,
            },
        },
        "tradingview_status": {
            "truthful_state": technical_state,
            "live_calls_enabled": technical_state == "ok",
            "provider_backed_record_count": 1 if technical_state == "ok" else 0,
        },
        "tradingview_context": {},
        "bookmap_context": {"sample": True},
        "nonlinear_comparisons": [
            {
                "comparison_id": "comparison:test",
                "generated_at": NOW,
                "instrument": "TEST",
                "horizon": "3d_forward",
                "verdict": "no_reliable_incremental_value",
                "hardware_used": False,
            }
        ],
    }


def _strategy_map() -> dict:
    return {
        "strategy_count": 1,
        "strategies": [
            {
                "strategy_family_id": "strategy:test",
                "instrument_contribution": {
                    "instruments": [{"symbol": "TEST", "paper_route_available": True}]
                },
            }
        ],
        "authority": authority_flags(),
    }


def _historical_result(hypothesis_id: str, holdout_return: float) -> dict:
    return {
        "hypothesis_id": hypothesis_id,
        "method_class": "qadam",
        "method_id": "lead_lag_event_study",
        "negative_control": False,
        "strategy_family_id": "strategy:test",
        "instrument": "TEST",
        "horizon": "3d_forward",
        "chronological": True,
        "cost_adjusted": True,
        "holdout_untouched_during_tuning": True,
        "independent_row_count": 240,
        "source_keys": ["source:a", "source:b"],
        "holdout_start_at": "2025-01-01T00:00:00+00:00",
        "holdout_end_at": "2025-06-01T00:00:00+00:00",
        "holdout_metrics": {
            "state": "measured",
            "mean_net_return": holdout_return,
            "cumulative_net_return": holdout_return * 20,
            "hit_rate": 0.6 if holdout_return > 0 else 0.4,
            "maximum_drawdown": -0.1 if holdout_return > 0 else -0.3,
            "trade_count": 20,
            "regime_mean_net_returns": {"normal": holdout_return},
        },
    }


def _folds(hypothesis_id: str) -> list[dict]:
    return [
        {
            "hypothesis_id": hypothesis_id,
            "test_metrics": {
                "mean_net_return": 0.01,
                "maximum_drawdown": -0.1,
                "trade_count": 20,
                "missing_cost_outcome_count": 0,
            },
        }
        for _ in range(3)
    ]


def test_truthful_current_context_can_pass_without_creating_authority() -> None:
    hypothesis = _hypothesis()
    context = assemble_current_akber_context(hypothesis, _current_artifacts(), generated_at=NOW)
    akber_input = build_akber_input(hypothesis, context, generated_at=NOW, strict_provenance=True)
    result = evaluate_akber_input(akber_input)

    assert set(akber_input["evidence"]) == set(CONTEXT_FIELDS)
    assert result["decision"] == "pass"
    assert result["router_eligible"] is True
    assert result["akber_pass_is_execution_approval"] is False
    assert result["execution_approval_created"] is False
    assert result["paper_order_created"] is False


def test_sample_tradingview_context_cannot_satisfy_confirmation() -> None:
    hypothesis = _hypothesis()
    context = assemble_current_akber_context(
        hypothesis,
        _current_artifacts(technical_state="sample_only"),
        generated_at=NOW,
    )
    akber_input = build_akber_input(hypothesis, context, generated_at=NOW, strict_provenance=True)
    result = evaluate_akber_input(akber_input)

    assert akber_input["evidence"]["technical_confirmation"]["available"] is False
    assert "technical_confirmation" in result["missing_critical_context"]
    assert result["decision"] == "hold_missing_context"
    assert result["router_eligible"] is False


def test_discovery_micro_can_use_one_of_four_confirmation_alternatives() -> None:
    hypothesis = _micro_hypothesis()
    context = assemble_current_akber_context(
        hypothesis,
        _current_artifacts(technical_state="sample_only"),
        generated_at=NOW,
    )
    akber_input = build_akber_input(
        hypothesis, context, generated_at=NOW, strict_provenance=True
    )
    result = evaluate_akber_input(akber_input)

    assert akber_input["experimental_tier"] == DISCOVERY_MICRO_TIER
    assert akber_input["evidence"]["technical_confirmation"]["available"] is False
    assert akber_input["confirmation_alternative_satisfied"] is True
    assert result["decision"] == "pass"
    assert result["router_eligible"] is True
    assert result["execution_approval_created"] is False


def test_discovery_micro_holds_without_any_confirmation_alternative() -> None:
    artifacts = _current_artifacts(technical_state="sample_only")
    artifacts["market_context"]["recent_packets"][0]["price_volume_context"][
        "records"
    ][0].pop("volume_ratio")
    artifacts["signal_integrity_reviews"] = []
    artifacts["nonlinear_comparisons"] = []
    context = assemble_current_akber_context(
        _micro_hypothesis(), artifacts, generated_at=NOW
    )
    akber_input = build_akber_input(
        _micro_hypothesis(), context, generated_at=NOW, strict_provenance=True
    )
    result = evaluate_akber_input(akber_input)

    assert "confirmation_alternative" in result["missing_critical_context"]
    assert result["decision"] == "hold_missing_context"


def test_discovery_micro_requires_market_data_for_the_execution_proxy() -> None:
    hypothesis = _micro_hypothesis()
    hypothesis["instrument_proxy_mapping"]["execution_proxy"] = "PROXY"
    context = assemble_current_akber_context(
        hypothesis, _current_artifacts(), generated_at=NOW
    )
    result = evaluate_akber_input(
        build_akber_input(
            hypothesis, context, generated_at=NOW, strict_provenance=True
        )
    )

    assert result["decision"] == "hold_missing_context"
    assert "fresh_catalyst" in result["missing_critical_context"]
    assert "volatility_context" in result["missing_critical_context"]


def test_discovery_micro_event_can_use_a_current_source_outside_historical_support() -> None:
    artifacts = _current_artifacts()
    artifacts["market_context"]["recent_packets"][0]["source_taxonomy"][0][
        "source_key"
    ] = "different-source"

    context = assemble_current_akber_context(
        _micro_hypothesis(), artifacts, generated_at=NOW
    )
    akber_input = build_akber_input(
        _micro_hypothesis(), context, generated_at=NOW, strict_provenance=True
    )
    result = evaluate_akber_input(akber_input)

    assert akber_input["evidence"]["fresh_catalyst"]["available"] is True
    assert akber_input["current_trigger_sources"] == ["different-source"]
    assert akber_input["evidence"]["volume_or_flow_confirmation"]["available"] is True
    assert result["decision"] == "pass"


def test_provider_availability_alone_cannot_become_an_event_trigger() -> None:
    artifacts = _current_artifacts()
    artifacts["market_context"]["recent_packets"][0][
        "research_goal_origin"
    ] = "provider_status"
    context = assemble_current_akber_context(
        _micro_hypothesis(), artifacts, generated_at=NOW
    )
    akber_input = build_akber_input(
        _micro_hypothesis(), context, generated_at=NOW, strict_provenance=True
    )

    assert akber_input["evidence"]["fresh_catalyst"]["available"] is False
    assert akber_input["missing_context_reasons"][0]["code"] == (
        "no_current_instrument_relevant_event"
    )


def test_regime_profile_requires_a_value_bearing_current_observation() -> None:
    hypothesis = _micro_hypothesis()
    hypothesis["pattern_lineage"]["evidence_profile"] = REGIME_STATE_PROFILE
    hypothesis["strategy_mapping"]["strategy_family_id"] = "silver_macro_liquidity_stress"
    artifacts = _current_artifacts()
    context = assemble_current_akber_context(hypothesis, artifacts, generated_at=NOW)
    held = build_akber_input(
        hypothesis, context, generated_at=NOW, strict_provenance=True
    )
    assert held["evidence"]["fresh_catalyst"]["available"] is False
    assert any(
        row["code"] == "current_regime_value_missing"
        for row in held["missing_context_reasons"]
    )

    artifacts["market_context"]["recent_packets"][0]["regime_observation"] = {
        "value": 1.25,
        "unit": "standard_deviations",
    }
    context = assemble_current_akber_context(hypothesis, artifacts, generated_at=NOW)
    admitted = build_akber_input(
        hypothesis, context, generated_at=NOW, strict_provenance=True
    )
    assert admitted["evidence"]["fresh_catalyst"]["available"] is True


def test_historical_decision_is_frozen_before_opposite_holdout_outcomes() -> None:
    positive = _historical_result("hypothesis:positive", 0.02)
    negative = _historical_result("hypothesis:negative", -0.02)
    replay = build_historical_akber_replay(
        [positive, negative],
        _folds("hypothesis:positive") + _folds("hypothesis:negative"),
        _strategy_map(),
        {"run_id": "backtest:test"},
        generated_at=NOW,
    )

    assert [record["decision"] for record in replay] == ["pass", "pass"]
    assert all(record["holdout_fields_used_to_make_decision"] == [] for record in replay)
    assert replay[0]["passed_positive_outcome"] is True
    assert replay[1]["passed_negative_outcome"] is True


def test_ablations_and_threshold_proposals_remain_research_only() -> None:
    replay = build_historical_akber_replay(
        [_historical_result("hypothesis:test", 0.01)],
        _folds("hypothesis:test"),
        _strategy_map(),
        {"run_id": "backtest:test"},
        generated_at=NOW,
    )
    ablations = build_stage_ablations(replay, generated_at=NOW)
    proposals = build_threshold_proposals(replay, generated_at=NOW, validated_edge_count=0)

    assert [record["stage_removed"] for record in ablations] == [
        "context",
        "catalyst",
        "confirmation",
        "risk",
        "execution",
        "postmortem_learning",
    ]
    assert all(record["threshold_change_applied"] is False for record in ablations)
    assert all(
        record["untouched_holdout_used_to_generate_proposal"] is False
        and record["threshold_change_applied"] is False
        and record["explicit_operator_review_required"] is True
        for record in proposals
    )


def test_zero_live_hypotheses_is_valid_when_historical_measurement_exists() -> None:
    result = _historical_result("hypothesis:test", 0.01)
    state = build_akber_filter_v3_from_inputs(
        [],
        {
            "implementation_complete": True,
            "admission_contract": "durable_or10_edge_registry_only",
            "hypothesis_count": 0,
            "edge_class_counts": {},
        },
        {
            "run_id": "backtest:test",
            "bulk_results": {
                "result_record_set_hash": "result-hash",
                "fold_record_set_hash": "fold-hash",
            },
        },
        [result],
        _folds("hypothesis:test"),
        _strategy_map(),
        {},
        generated_at=NOW,
    )

    assert validate_akber_filter_v3_state(state) == []
    assert state["dashboard"]["valid_no_current_hypothesis_outcome"] is True
    assert state["dashboard"]["net_historical_contribution_measurable"] is True
    assert state["inputs"] == []
    assert state["results"] == []
    assert len(state["replay"]) == 1
    assert len(state["ablation"]) == 6
    assert len(state["threshold_proposals"]) == 5


def test_zero_live_hypotheses_is_valid_when_all_history_is_honestly_excluded() -> None:
    incomplete = _historical_result("hypothesis:incomplete", 0.01)
    incomplete["holdout_metrics"]["state"] = "unavailable"
    state = build_akber_filter_v3_from_inputs(
        [],
        {
            "implementation_complete": True,
            "admission_contract": "durable_or10_edge_registry_only",
            "hypothesis_count": 0,
            "edge_class_counts": {},
        },
        {
            "run_id": "backtest:test",
            "bulk_results": {
                "result_record_set_hash": "result-hash",
                "fold_record_set_hash": "fold-hash",
            },
        },
        [incomplete],
        _folds("hypothesis:incomplete"),
        _strategy_map(),
        {},
        generated_at=NOW,
    )

    assert validate_akber_filter_v3_state(state) == []
    assert state["dashboard"]["valid_no_current_hypothesis_outcome"] is True
    assert state["dashboard"]["historical_replay_unavailable"] is True
    assert state["dashboard"]["historical_measurement_state"] == (
        "unavailable_no_complete_untouched_holdout_outcomes"
    )
    assert state["dashboard"]["net_historical_contribution_measurable"] is False
    assert state["replay"] == []
    assert state["ablation"] == []


def test_current_akber_input_is_bound_to_exactly_one_decision_packet() -> None:
    hypothesis = _hypothesis()
    context = assemble_current_akber_context(
        hypothesis, _current_artifacts(), generated_at=NOW
    )
    packet = {
        "decision_evidence_packet_id": "decision-packet:test",
        "decision_generation_id": "decision-generation:test",
        "hypothesis_id": hypothesis["hypothesis_id"],
        "mixed_generation_join": False,
        "akber_context": context,
    }
    result = _historical_result("hypothesis:history", 0.01)
    state = build_akber_filter_v3_from_inputs(
        [hypothesis],
        {
            "implementation_complete": True,
            "admission_contract": "durable_or10_edge_registry_only",
            "hypothesis_count": 1,
            "edge_class_counts": {"validated_research_edge": 1},
        },
        {
            "run_id": "backtest:test",
            "bulk_results": {
                "result_record_set_hash": "result-hash",
                "fold_record_set_hash": "fold-hash",
            },
        },
        [result],
        _folds("hypothesis:history"),
        _strategy_map(),
        _current_artifacts(),
        generated_at=NOW,
        decision_evidence_packets=[packet],
    )

    assert validate_akber_filter_v3_state(state) == []
    assert state["inputs"][0]["decision_evidence_packet_id"] == "decision-packet:test"
    assert state["inputs"][0]["decision_generation_id"] == "decision-generation:test"
    assert state["input_lineage"]["decision_evidence_packet_mode"] is True


def test_adverse_context_vetoes_even_when_other_fields_are_complete() -> None:
    hypothesis = _hypothesis()
    context = assemble_current_akber_context(hypothesis, _current_artifacts(), generated_at=NOW)
    adverse = deepcopy(context)
    adverse["risk_reward_context"]["details"]["expected_net_return"] = -0.01
    adverse["risk_reward_context"]["value"]["expected_net_return"] = -0.01
    result = evaluate_akber_input(
        build_akber_input(hypothesis, adverse, generated_at=NOW, strict_provenance=True)
    )

    assert result["decision"] == "veto"
    assert "expected_return_non_positive_after_costs" in result["hard_vetoes"]


def test_defined_but_weak_reward_to_risk_is_adverse_not_missing() -> None:
    hypothesis = _hypothesis()
    hypothesis["risk_concept"]["expected_reward_to_risk"] = 0.5
    context = assemble_current_akber_context(
        hypothesis, _current_artifacts(), generated_at=NOW
    )
    akber_input = build_akber_input(
        hypothesis, context, generated_at=NOW, strict_provenance=True
    )
    result = evaluate_akber_input(akber_input)

    assert akber_input["evidence"]["risk_reward_context"]["available"] is True
    assert "risk_reward_context" not in result["missing_critical_context"]
    assert result["decision"] == "veto"
    assert "reward_to_risk_below_frozen_floor" in result["hard_vetoes"]
