import copy

from orchestrator.qsase_learning_attribution_ledger import (
    LEARNING_AUTHORITY_FLAGS,
    build_learning_attribution_ledger,
    validate_learning_attribution_ledger,
    validate_negative_learning_attribution_ledger_probes,
)


def test_learning_attribution_ledger_separates_evidence_classes_and_components():
    payload = build_learning_attribution_ledger()

    assert payload["attribution_record_count"] > 0
    assert payload["non_trade_record_count"] > 0
    assert payload["shadow_replay_record_count"] > 0
    assert payload["backtest_record_count"] > 0
    assert payload["rejected_hypothesis_record_count"] > 0
    assert payload["blocked_route_record_count"] > 0
    assert payload["system_defect_record_count"] > 0
    assert validate_learning_attribution_ledger(payload) == []

    classes = {record["evidence_class"] for record in payload["attribution_records"]}
    assert "backtest_observation" in classes
    assert "shadow_replay" in classes
    assert "non_trade_decision" in classes
    assert "rejected_hypothesis" in classes
    assert "blocked_route" in classes
    assert "system_defect" in classes

    for record in payload["attribution_records"]:
        assert record["status"] == "recorded_proposal_only"
        assert record["component_attribution"]["akber_filter"]["contribution"] in {
            "helped",
            "hurt",
            "neutral",
            "unknown",
            "blocked",
            "not_applicable",
        }
        assert record["proposal"]["approval_required"] is True
        assert record["proposal"]["apply_allowed"] is False
        assert record["proposal"]["applied"] is False


def test_learning_attribution_proposals_are_review_only_and_system_defects_do_not_mutate_strategy():
    payload = build_learning_attribution_ledger()
    defect_ids = {record["attribution_record_id"] for record in payload["system_defect_records"]}

    assert payload["approval_required_count"] == payload["active_proposal_count"]
    assert payload["approved_proposal_count"] == 0
    assert payload["applied_update_count"] == 0
    assert payload["learning_write_created"] is False
    assert payload["strategy_mutation_created"] is False
    assert payload["policy_mutation_created"] is False
    assert payload["model_weight_update_created"] is False
    assert payload["trust_score_update_created"] is False

    for proposal_artifact in (
        payload["strategy_weight_proposals"],
        payload["source_trust_proposals"],
        payload["model_weight_proposals"],
        payload["filter_threshold_proposals"],
    ):
        assert proposal_artifact["applied_update_count"] == 0
        assert proposal_artifact["apply_allowed"] is False
        assert proposal_artifact["applied"] is False
        for proposal in proposal_artifact["proposals"]:
            assert proposal["approval_required"] is True
            assert proposal["apply_allowed"] is False
            assert proposal["applied"] is False

    for proposal in payload["strategy_weight_proposals"]["proposals"]:
        assert not any(str(ref).split("#")[-1] in defect_ids for ref in proposal["evidence_refs"])


def test_learning_attribution_has_no_order_proof_or_live_authority_and_dashboard_is_safe():
    payload = build_learning_attribution_ledger()

    assert payload["authority_flags"] == LEARNING_AUTHORITY_FLAGS
    assert all(value is False for value in payload["authority"].values())
    assert payload["paper_order_created_count"] == 0
    assert payload["broker_write_count"] == 0
    assert payload["proof_credit_allowed"] is False
    assert payload["paper_proof_ledger_credit_allowed"] is False
    assert payload["live_capital_enabled"] is False
    assert payload["paper_growth_trial_calendar_advanced"] is False

    summary = payload["dashboard_safe_summary"]
    assert summary["decision_record_based"] is True
    assert summary["essay_free"] is True
    assert summary["command_disabled"] is True
    assert summary["live_send_allowed"] is False
    assert summary["proposal_applied"] is False
    assert summary["no_paper_orders_created"] is True
    assert summary["no_proof_credit_granted"] is True

    for record in payload["attribution_records"]:
        assert all(record[flag] is False for flag in LEARNING_AUTHORITY_FLAGS)
        assert all(record["authority"][flag] is False for flag in LEARNING_AUTHORITY_FLAGS)
        assert record["telegram_summary"]["review_only"] is True
        assert record["telegram_summary"]["command_disabled"] is True
        assert record["telegram_summary"]["contains_command"] is False
        assert record["telegram_summary"]["contains_broker_instruction"] is False


def test_learning_attribution_negative_probes_catch_mutations():
    payload = build_learning_attribution_ledger()

    applied_probe = copy.deepcopy(payload)
    applied_probe["strategy_weight_proposals"]["proposals"][0]["applied"] = True
    assert any("proposal_applied" in error for error in validate_learning_attribution_ledger(applied_probe))

    order_probe = copy.deepcopy(payload)
    order_probe["paper_order_created_count"] = 1
    assert any("paper_order_created_count" in error for error in validate_learning_attribution_ledger(order_probe))

    assert validate_negative_learning_attribution_ledger_probes() == []
