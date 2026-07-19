import copy

from orchestrator.qsase_paperops_gate_interface import (
    HANDOFF_AUTHORITY_FLAGS,
    build_paperops_gate_interface,
    validate_negative_paperops_gate_interface_probes,
    validate_paperops_gate_interface,
    validate_paperops_handoff_record,
)


def test_paperops_gate_interface_rejects_non_candidates_with_lineage_and_idempotency():
    payload = build_paperops_gate_interface()

    assert payload["gate_record_count"] > 0
    assert payload["router_candidate_count"] == 0
    assert payload["handoff_record_count"] == 0
    assert payload["eligible_for_paperops_review_count"] == 0
    assert (
        payload["eligible_for_paperops_review_count"]
        + payload["held_handoff_count"]
        + payload["rejected_handoff_count"]
    ) == payload["gate_record_count"]
    assert payload["duplicate_idempotency_count"] == 0
    assert payload["paper_route_unavailable_count"] == 0
    assert payload["guarded_alpaca_paper_route_state"] == "available_for_review"
    assert validate_paperops_gate_interface(payload) == []

    for record in payload["gate_records"]:
        assert record["status"] in {"hold_route_unavailable", "rejected_before_paperops"}
        assert record["research_goal_lineage"]["research_goal_id"]
        assert record["candidate_identity"]["candidate_id"]
        assert record["candidate_identity"]["candidate_identity_hash"]
        assert record["idempotency"]["idempotency_namespace"] == "qsase_paperops_review"
        assert record["idempotency"]["idempotency_seed"]
        assert record["idempotency"]["idempotency_key"]
        assert record["idempotency"]["duplicate_idempotency_detected"] is False
        assert record["idempotency"]["candidate_specific_duplicate_check_required_downstream"] is True
        assert "source_quorum" in record["gate_state"]
        assert "akber_filter" in record["gate_state"]
        assert "quantum_review" in record["gate_state"]
        assert "qctrl_paper_consultation" in record["gate_state"]
        assert record["gate_state"]["guarded_alpaca_paper_route_name"] == "existing guarded Alpaca Paper route only"


def test_paperops_gate_interface_boundaries_dashboard_and_synthetic_handoff_validation():
    payload = build_paperops_gate_interface()
    record = copy.deepcopy(payload["gate_records"][0])

    assert payload["existing_paperops_remains_only_submit_route"] is True
    assert payload["dashboard_safe_summary"]["authority_state"] == "paperops_handoff_context_only_no_order"
    assert payload["dashboard_safe_summary"]["no_qualified_setups_created"] is True
    assert payload["dashboard_safe_summary"]["no_paper_orders_created"] is True
    assert payload["dashboard_safe_summary"]["no_proof_credit_granted"] is True
    assert payload["qctrl_paper_consultation_state"] in {"not_bypassed", "hold"}
    assert payload["guarded_alpaca_paper_route_name"] == "existing guarded Alpaca Paper route only"

    record["status"] = "eligible_for_existing_paperops_review"
    record["idempotency"]["duplicate_idempotency_detected"] = False
    record["decision"]["paperops_gate_output"] = "eligible_for_existing_paperops_review"
    record["decision"]["reason"] = "synthetic_validation_only"
    assert validate_paperops_handoff_record(record) == []


def test_paperops_gate_interface_has_no_order_authority_and_negative_probes():
    payload = build_paperops_gate_interface()

    assert payload["authority_flags"] == HANDOFF_AUTHORITY_FLAGS
    assert all(value is False for value in payload["authority"].values())
    assert payload["paper_order_created_count"] == 0
    assert payload["qualified_setup_created_count"] == 0
    assert payload["trade_candidate_created_count"] == 0
    assert payload["risk_approval_created_count"] == 0
    assert payload["execution_approval_created_count"] == 0
    assert payload["broker_write_count"] == 0
    assert payload["proof_credit_allowed"] is False
    assert payload["live_capital_enabled"] is False

    for record in payload["gate_records"]:
        assert record["decision"]["paper_order_ready"] is False
        assert record["decision"]["qualified_setup_created"] is False
        assert record["decision"]["paper_order_created"] is False
        assert record["decision"]["broker_write_created"] is False
        assert record["decision"]["proof_credit_allowed"] is False
        assert record["telegram_summary"]["review_only"] is True
        assert record["telegram_summary"]["command_disabled"] is True
        assert record["telegram_summary"]["contains_command"] is False
        assert record["telegram_summary"]["contains_broker_instruction"] is False
        assert all(record[flag] is False for flag in HANDOFF_AUTHORITY_FLAGS)
        assert all(record["authority"][flag] is False for flag in HANDOFF_AUTHORITY_FLAGS)

    assert validate_negative_paperops_gate_interface_probes() == []
