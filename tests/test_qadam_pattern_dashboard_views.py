from __future__ import annotations

from orchestrator.qadam_pattern_dashboard_views import (
    PUBLIC_AUTHORITY,
    build_pattern_dashboard_views,
    build_pattern_discovery_projection,
    build_quantum_review_projection,
    validate_pattern_dashboard_views,
)


def _score(
    *,
    family: str = "silver_macro_liquidity_stress",
    instrument: str = "SLV",
    score: float = 0.42,
) -> dict:
    return {
        "strategy_family_id": family,
        "strategy_label": "Silver Macro Liquidity Stress",
        "instrument": instrument,
        "direction_hypothesis": "upside_under_confirmed_liquidity_stress",
        "horizon_hypothesis": "5d_forward",
        "raw_pattern_score": score,
        "score_is_probability": False,
        "confidence_state": "score_ready_for_tape",
        "scoring_as_of": "2026-07-11T10:00:00+00:00",
        "missing_critical_features": ["current_market_price"],
        "negative_control": False,
        "feature_inputs": [
            {
                "source_key": "fred",
                "fresh": True,
                "independence_cluster_id": "macro",
            },
            {
                "source_key": "bis",
                "fresh": True,
                "independence_cluster_id": "banking",
            },
        ],
    }


def _empty_inputs() -> dict:
    return {
        "generated_at": "2026-07-11T10:05:00+00:00",
        "scores": [],
        "edges": [],
        "score_tape": {},
        "forward_labels": {},
        "backtest": {},
        "edge_summary": {"validated_edge_count": 0},
        "backfill": {"source_count": 41, "instrument_count": 19},
        "comparisons": [],
    }


def test_frozen_pattern_views_are_distinct_honest_and_qualitative(monkeypatch) -> None:
    from orchestrator import qadam_pattern_dashboard_views as module
    families = ["silver_macro_liquidity_stress", "semiconductor_policy_options_asymmetry",
                "prediction_market_geopolitical_dislocation", "defence_repricing_geopolitical_watch",
                "crude_oil_energy_security_disruption"]
    records = {
        module.PATTERN_SCORE_ARTIFACT: [_score(family=family) for family in families],
        module.NONLINEAR_EXPERIMENT_ARTIFACT: [{
            "experiment_id": "fixture:protocol", "strategy_family_id": families[0],
            "method": "ordinal_permutation_entropy", "status": "blocked_no_untouched_holdout",
            "reproducibility_state": "manifest_defined_no_empirical_run",
            "generated_at": "2026-07-11T10:00:00+00:00"}],
    }
    monkeypatch.setattr(module, "read_jsonl", lambda path: records.get(path.name, []))
    monkeypatch.setattr(module, "read_json", lambda path: {})
    views = build_pattern_dashboard_views(generated_at="2026-07-11T10:05:00+00:00")
    discovery = views["pattern_discovery"]
    quantum = views["quantum_review"]
    assert validate_pattern_dashboard_views(views) == []
    assert discovery["relationship_count"] == 5
    assert discovery["qualitative_analysis"]["bullet_count"] == 5
    assert all(
        isinstance(bullet["raw_pattern_score"], float)
        for bullet in discovery["qualitative_analysis"]["bullets"]
    )
    assert discovery["spotlight"] is None
    assert all(
        relationship["raw_pattern_score_is_probability"] is False
        for relationship in discovery["relationships"]
    )
    assert quantum["empirical_comparison_count"] >= 0
    assert quantum["defined_protocol_count"] > 0
    assert quantum["current_method_state"]["hardware_completed_count"] == 0
    if quantum["empirical_comparison_count"]:
        assert quantum["current_method_state"]["simulator_completed_count"] > 0
        assert quantum["strengthened_count"] == 0
        assert all(
            review["contribution"] in {"neutral", "not_useful"} for review in quantum["reviews"]
        )
    else:
        assert all(review["verdict"] == "not_measurable" for review in quantum["reviews"])
        assert all(review["execution_mode"] == "not_run" for review in quantum["reviews"])


def test_pattern_projection_groups_proxy_instruments_into_one_relationship() -> None:
    inputs = _empty_inputs()
    inputs["scores"] = [_score(instrument="SLV"), _score(instrument="SIL", score=0.38)]
    discovery = build_pattern_discovery_projection(**inputs)
    assert discovery["relationship_count"] == 1
    relationship = discovery["relationships"][0]
    assert relationship["target_instruments"] == ["SIL", "SLV"]
    assert relationship["stage"] == "awaiting_historical_evidence"
    assert relationship["next_destination"]["view_id"] == "replay"
    assert relationship["historical_evidence"]["validated_edge"] is False


def test_pattern_projection_explains_score_records_without_inflating_discoveries() -> None:
    inputs = _empty_inputs()
    strategy_scores = [_score(instrument="SLV"), _score(instrument="SIL", score=0.38)]
    context_score = _score(instrument="SPY", score=0.11)
    context_score["strategy_family_id"] = None
    context_score["strategy_agnostic"] = True
    context_score["negative_control"] = True
    inputs["scores"] = [*strategy_scores, context_score]
    discovery = build_pattern_discovery_projection(**inputs)
    analysis = discovery["qualitative_analysis"]
    recorded = next(row for row in discovery["funnel"] if row["key"] == "recorded")

    assert discovery["relationship_count"] == 1
    assert analysis["bullet_count"] == 1
    assert analysis["total_score_record_count"] == 3
    assert analysis["strategy_linked_score_record_count"] == 2
    assert analysis["context_and_control_score_record_count"] == 1
    assert "not additional discoveries" in analysis["score_record_explanation"]
    assert recorded == {
        "key": "recorded",
        "label": "Instrument score records",
        "count": 3,
    }


def test_pattern_projection_requires_real_edge_evidence_before_validation() -> None:
    inputs = _empty_inputs()
    inputs["scores"] = [_score()]
    inputs["edges"] = [
        {
            "strategy_family_id": "silver_macro_liquidity_stress",
            "edge_state": "validated_edge",
            "net_expectancy": 0.01,
        }
    ]
    inputs["edge_summary"] = {"validated_edge_count": 1}
    discovery = build_pattern_discovery_projection(**inputs)
    relationship = discovery["relationships"][0]
    assert relationship["stage"] == "validated_edge"
    assert relationship["historical_evidence"]["validated_edge"] is True
    assert relationship["next_destination"]["view_id"] == "strategies"
    assert discovery["spotlight"]["pattern_id"] == relationship["pattern_id"]


def test_quantum_protocol_is_not_counted_as_empirical_comparison() -> None:
    inputs = _empty_inputs()
    inputs["scores"] = [_score()]
    discovery = build_pattern_discovery_projection(**inputs)
    protocol = {
        "experiment_id": "exp-1",
        "strategy_family_id": "silver_macro_liquidity_stress",
        "method": "ordinal_permutation_entropy",
        "status": "blocked_no_untouched_holdout",
        "reproducibility_state": "manifest_defined_no_empirical_run",
        "fallback": "deterministic_classical_shadow",
        "generated_at": "2026-07-11T10:00:00+00:00",
    }
    comparison = {
        "experiment_id": "exp-1",
        "strategy_family_id": "silver_macro_liquidity_stress",
        "method": "ordinal_permutation_entropy",
        "classical_holdout_metric": None,
        "nonlinear_or_quantum_holdout_metric": None,
        "incremental_holdout_value": None,
        "hardware_used": False,
        "verdict": "not_measurable_without_untouched_holdout",
        "generated_at": "2026-07-11T10:00:00+00:00",
    }
    quantum = build_quantum_review_projection(
        generated_at="2026-07-11T10:05:00+00:00",
        pattern_discovery=discovery,
        protocols=[protocol],
        comparisons=[comparison],
        usefulness={},
        overfit={"status": "protocol_ready_no_experiments_run"},
    )
    assert quantum["defined_protocol_count"] == 1
    assert quantum["empirical_comparison_count"] == 0
    assert quantum["reviews"][0]["execution_mode"] == "not_run"
    assert quantum["reviews"][0]["verdict"] == "not_measurable"
    assert quantum["reviews"][0]["hardware_used"] is False


def test_positive_raw_delta_does_not_override_controlled_quantum_verdict() -> None:
    inputs = _empty_inputs()
    inputs["scores"] = [_score()]
    discovery = build_pattern_discovery_projection(**inputs)
    protocol = {
        "experiment_id": "exp-controlled-hold",
        "strategy_family_id": "silver_macro_liquidity_stress",
        "method": "quantum_kernel_or_circuit_inspired",
        "status": "measured",
        "generated_at": "2026-07-11T10:00:00+00:00",
    }
    comparison = {
        "experiment_id": "exp-controlled-hold",
        "strategy_family_id": "silver_macro_liquidity_stress",
        "method": "quantum_kernel_or_circuit_inspired",
        "classical_holdout_metric": 0.01,
        "nonlinear_or_quantum_holdout_metric": 0.02,
        "incremental_holdout_value": 0.01,
        "quantum_usefulness_score": 0.0,
        "verdict": "not_useful_for_this_edge",
        "simulation_used": True,
        "hardware_used": False,
        "generated_at": "2026-07-11T10:00:00+00:00",
    }
    quantum = build_quantum_review_projection(
        generated_at="2026-07-11T10:05:00+00:00",
        pattern_discovery=discovery,
        protocols=[protocol],
        comparisons=[comparison],
        usefulness={"quantum_usefulness_score": 0.0},
        overfit={"status": "passed"},
    )
    review = quantum["reviews"][0]
    assert review["verdict"] == "classical_preferred"
    assert review["contribution"] == "not_useful"
    assert quantum["strengthened_count"] == 0
    assert quantum["current_method_state"]["simulator_completed_count"] == 1
    assert quantum["current_method_state"]["hardware_completed_count"] == 0


def test_explicit_incremental_verdict_is_required_for_strengthening() -> None:
    inputs = _empty_inputs()
    inputs["scores"] = [_score()]
    discovery = build_pattern_discovery_projection(**inputs)
    protocol = {
        "experiment_id": "exp-controlled-pass",
        "strategy_family_id": "silver_macro_liquidity_stress",
        "method": "quantum_kernel_or_circuit_inspired",
        "status": "measured",
        "generated_at": "2026-07-11T10:00:00+00:00",
    }
    comparison = {
        "experiment_id": "exp-controlled-pass",
        "strategy_family_id": "silver_macro_liquidity_stress",
        "method": "quantum_kernel_or_circuit_inspired",
        "classical_holdout_metric": 0.01,
        "nonlinear_or_quantum_holdout_metric": 0.02,
        "incremental_holdout_value": 0.01,
        "quantum_usefulness_score": 0.006,
        "verdict": "useful_incremental_value_research_only",
        "simulation_used": True,
        "hardware_used": False,
        "generated_at": "2026-07-11T10:00:00+00:00",
    }
    quantum = build_quantum_review_projection(
        generated_at="2026-07-11T10:05:00+00:00",
        pattern_discovery=discovery,
        protocols=[protocol],
        comparisons=[comparison],
        usefulness={"quantum_usefulness_score": 0.006},
        overfit={"status": "passed"},
    )
    review = quantum["reviews"][0]
    assert review["verdict"] == "nonlinear_strengthened"
    assert review["contribution"] == "incremental"
    assert review["net_usefulness"] == 0.006
    assert quantum["strengthened_count"] == 1


def test_dashboard_projections_preserve_non_authority_flags() -> None:
    views = build_pattern_dashboard_views()
    for payload in views.values():
        for field, expected in PUBLIC_AUTHORITY.items():
            assert payload[field] is expected
        assert payload["paper_order_allowed"] is False
        assert payload["broker_write_allowed"] is False
        assert payload["live_capital_enabled"] is False
