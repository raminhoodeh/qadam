from __future__ import annotations

from orchestrator.qadam_clean_epoch_quiescence import validate_clean_epoch_quiescence


def test_quiescence_rejects_false_safe_checkpoint() -> None:
    payload = {
        "quiescent": True,
        "operator_service_running": True,
        "active_worker_count": 0,
        "ambiguous_or_unresolved_order_count": 0,
        "research_lock_active": True,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "authority": {
            "paper_only": True,
            "read_only": True,
            "command_disabled": True,
            "broker_write_allowed": False,
            "broker_write_count": 0,
            "live_broker_endpoint_allowed": False,
            "live_capital_enabled": False,
            "paper_order_allowed": False,
            "paper_order_created": False,
            "paper_order_created_count": 0,
            "risk_approval_allowed": False,
            "risk_approval_created": False,
            "execution_approval_allowed": False,
            "execution_approval_created": False,
            "trade_candidate_creation_allowed": False,
            "trade_candidate_created": False,
            "qualified_setup_created": False,
            "proof_credit_allowed": False,
            "paper_proof_ledger_credit_allowed": False,
            "telegram_command_path_enabled": False,
            "telegram_trade_command_enabled": False,
            "telegram_live_send_allowed": False,
            "policy_mutation_allowed": False,
            "autonomous_code_edit_allowed": False,
            "paper_growth_trial_calendar_advance_allowed": False,
            "simulated_elapsed_time_allowed": False,
            "proposal_first": True,
        },
    }
    assert "quiescence_passed_with_active_state:operator_service_running" in (
        validate_clean_epoch_quiescence(payload)
    )
