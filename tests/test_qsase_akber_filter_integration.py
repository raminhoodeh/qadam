from orchestrator.qsase_akber_filter_integration import (
    AKBER_AUTHORITY_FLAGS,
    DASHBOARD_AKBER_STAGES,
    INTERNAL_AKBER_STAGES,
    build_akber_filter_results,
    score_akber_filter_stage,
    validate_akber_filter_results,
    validate_negative_akber_filter_probes,
)


def test_akber_filter_records_six_stage_vetoes_and_router_visibility():
    payload = build_akber_filter_results()

    assert payload["input_filter_record_count"] > 0
    assert set(INTERNAL_AKBER_STAGES).issubset(payload["internal_akber_stages"])
    assert set(DASHBOARD_AKBER_STAGES).issubset(payload["dashboard_akber_stages"])
    assert payload["rejected_filter_count"] > 0
    assert payload["candidate_for_router_count"] == 0
    assert validate_akber_filter_results(payload) == []

    for result in payload["akber_filter_results"]:
        assert set(INTERNAL_AKBER_STAGES).issubset(result["stage_state"])
        assert set(DASHBOARD_AKBER_STAGES).issubset(result["dashboard_stage_state"])
        assert result["decision"]["filter_decision"] in {
            "pass",
            "hold_missing_context",
            "hold_wait_for_confirmation",
            "reject",
            "audit_only",
        }
        assert result["decision"]["reason"]
        if result["decision"]["filter_decision"] == "reject":
            assert result["decision"]["veto_reason"]
            assert result["router_output"]["candidate_for_router"] is False
        assert result["router_output"]["router_visible"] is True
        assert result["decision"]["akber_filter_pass_is_not_execution_approval"] is True


def test_akber_filter_ablation_thresholds_and_dashboard_are_proposal_only():
    payload = build_akber_filter_results()
    thresholds = payload["threshold_proposals"]
    ablation = payload["ablation"]

    assert thresholds["status"] == "threshold_proposals_recorded_not_applied"
    assert thresholds["threshold_change_applied"] is False
    assert thresholds["proposal_count"] == len(INTERNAL_AKBER_STAGES)
    assert all(proposal["threshold_change_applied"] is False for proposal in thresholds["proposals"])
    assert ablation["historical_filter_replay_exists"] is True
    assert "filter_contribution_attribution" in ablation
    assert payload["dashboard_safe_summary"]["authority_state"] == "akber_filter_not_execution_approval"
    assert payload["dashboard_safe_summary"]["no_trade_candidates_created"] is True

    stage_score = score_akber_filter_stage("obv_volume", {})
    assert stage_score["state"] == "missing_volume_confirmation"
    assert stage_score["missing_context"] is True


def test_akber_filter_has_no_execution_or_order_authority_and_negative_probes():
    payload = build_akber_filter_results()

    assert payload["authority_flags"] == AKBER_AUTHORITY_FLAGS
    assert all(value is False for value in payload["authority"].values())
    assert payload["akber_filter_pass_is_not_execution_approval"] is True
    assert payload["execution_allowed"] is False
    assert payload["paper_order_allowed"] is False
    assert payload["trade_candidate_created"] is False
    assert payload["qualified_setup_created"] is False
    assert payload["proof_credit_allowed"] is False
    assert payload["live_capital_enabled"] is False

    for result in payload["akber_filter_results"]:
        assert result["telegram_summary"]["review_only"] is True
        assert result["telegram_summary"]["command_disabled"] is True
        assert result["telegram_summary"]["contains_command"] is False
        assert result["telegram_summary"]["contains_broker_instruction"] is False
        assert all(result[flag] is False for flag in AKBER_AUTHORITY_FLAGS)

    assert validate_negative_akber_filter_probes() == []
