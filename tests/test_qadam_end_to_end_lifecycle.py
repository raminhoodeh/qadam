from orchestrator.qadam_end_to_end_lifecycle import (
    ROUTE_ORDER,
    STAGE_IDS,
    build_lifecycle_contract,
    build_lifecycle_dashboard_summary,
    build_route_stage_map,
    validate_lifecycle_contract,
    validate_lifecycle_summary,
)


def _freshness(*artifact_names: str) -> dict:
    return {
        "status": "fresh",
        "records": [
            {
                "artifact": f"data/runtime/{name}",
                "freshness_state": "fresh",
                "generated_at": "2026-07-12T08:00:00+00:00",
            }
            for name in artifact_names
        ],
    }


def _complete_context() -> dict:
    return {
        "source_summary": {"source_count": 41, "fresh_count": 41},
        "trading_universe": {"watched_instrument_count": 21},
        "backfill_progress": {"completed_jobs": 21, "total_jobs": 21},
        "findings": [{"pattern_id": "p1"}, {"pattern_id": "p2"}],
        "quantum_review": {"empirical_comparison_count": 2},
        "hypotheses": [{"hypothesis_id": "h1"}],
        "foundry": {"status": "ready"},
        "edge_summary": {"validated_edge_count": 1},
        "shadow_state": {"decision_count": 4},
        "akber_results": [{"decision": "pass"}],
        "router_scoreboard": {
            "decision_count": 1,
            "paper_review_candidate_count": 1,
        },
        "router_why_not": {},
        "handoff_count": 1,
        "release": {"release_effective": True},
        "lifecycle": {"order_count": 1, "ambiguous_lifecycle_count": 0},
        "current_portfolio": {"position_count": 1},
        "learning_cycle": {
            "counts": {
                "learnable_event_count": 1,
                "qadam_origin_outcome_count": 1,
                "proof_eligible_count": 0,
            }
        },
        "improvement_pipeline": {
            "counts": {"active_candidate_count": 1, "applied_version_count": 0}
        },
        "freshness": _freshness(
            "qadam_source_operational_state.jsonl",
            "qadam_backfill_coverage.json",
            "qadam_pattern_score_v3_records.jsonl",
            "qadam_strategy_hypotheses_v3.jsonl",
            "qadam_edge_registry_summary.json",
            "qadam_akber_filter_v3_results.jsonl",
            "qadam_router_v3_scoreboard.json",
            "qadam_paper_lifecycle_v3.json",
            "qadam_learning_cycle_dashboard.json",
            "qadam_improvement_pipeline_dashboard.json",
        ),
    }


def test_contract_maps_all_ten_stages_and_thirteen_routes():
    contract = build_lifecycle_contract(generated_at="2026-07-12T08:00:00+00:00")
    route_map = build_route_stage_map(generated_at="2026-07-12T08:00:00+00:00")

    assert contract["stage_count"] == 10
    assert [stage["stage_id"] for stage in contract["stages"]] == list(STAGE_IDS)
    assert [stage["number"] for stage in contract["stages"]] == list(range(1, 11))
    assert set(contract["route_contexts"]) == set(ROUTE_ORDER)
    assert route_map["route_order"] == list(ROUTE_ORDER)
    assert contract["single_global_current_stage"] is False
    assert contract["concurrent_item_lifecycles_supported"] is True
    assert validate_lifecycle_contract(contract) == []


def test_runtime_summary_separates_stage_activity_from_page_ownership():
    summary = build_lifecycle_dashboard_summary(
        _complete_context(),
        generated_at="2026-07-12T08:00:00+00:00",
    )

    assert summary["stage_count"] == 10
    assert set(summary["stage_states"]) == set(STAGE_IDS)
    assert summary["stage_states"]["observe_world"]["state"] == "active"
    assert summary["stage_states"]["validate_edge"]["state"] == "active"
    assert summary["stage_states"]["govern_decision"]["state"] == "active"
    assert summary["single_global_current_stage"] is False
    assert summary["paper_order_created_count"] == 0
    assert summary["broker_write_count"] == 0
    assert summary["proof_credit_allowed"] is False
    assert summary["live_capital_enabled"] is False
    assert validate_lifecycle_summary(summary) == []


def test_missing_runtime_inputs_fail_closed_without_hiding_the_structure():
    summary = build_lifecycle_dashboard_summary(
        {},
        generated_at="2026-07-12T08:00:00+00:00",
    )

    assert len(summary["stages"]) == 10
    assert summary["stage_states"]["observe_world"]["state"] == "unavailable"
    assert summary["stage_states"]["qualify_evidence"]["state"] == "unavailable"
    assert summary["stage_states"]["discover_patterns"]["state"] == "unavailable"
    assert summary["stage_states"]["execute_monitor"]["state"] == "idle"
    assert all(record["summary"] for record in summary["stage_states"].values())
    assert all(record["artifact_refs"] for record in summary["stage_states"].values())
    assert validate_lifecycle_summary(summary) == []
