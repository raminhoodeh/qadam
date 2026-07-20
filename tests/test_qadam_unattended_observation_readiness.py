from __future__ import annotations

from copy import deepcopy

from orchestrator.qadam_unattended_observation_readiness import (
    validate_unattended_observation_readiness,
)


def _payload() -> dict:
    return {
        "safe_to_leave_running_and_observe": True,
        "engineering_blockers": [],
        "engineering_checks": {"live_capital_disabled": True},
        "simulated_elapsed_time_used": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "authority": {
            "paper_only": True,
            "read_only": True,
            "command_disabled": True,
            "proposal_first": True,
            "trade_candidate_creation_allowed": False,
            "trade_candidate_created": False,
            "qualified_setup_created": False,
            "risk_approval_allowed": False,
            "risk_approval_created": False,
            "execution_approval_allowed": False,
            "execution_approval_created": False,
            "paper_order_allowed": False,
            "paper_order_created": False,
            "paper_order_created_count": 0,
            "broker_write_allowed": False,
            "broker_write_count": 0,
            "live_capital_enabled": False,
            "live_broker_endpoint_allowed": False,
            "proof_credit_allowed": False,
            "paper_proof_ledger_credit_allowed": False,
            "paper_growth_trial_calendar_advance_allowed": False,
            "simulated_elapsed_time_allowed": False,
            "telegram_command_path_enabled": False,
            "telegram_trade_command_enabled": False,
            "telegram_live_send_allowed": False,
            "policy_mutation_allowed": False,
            "autonomous_code_edit_allowed": False,
        },
    }


def test_observation_readiness_is_distinct_from_edge_or_soak_maturity() -> None:
    assert validate_unattended_observation_readiness(_payload()) == []


def test_observation_readiness_fails_closed_with_engineering_blocker() -> None:
    payload = deepcopy(_payload())
    payload["engineering_blockers"] = ["operator_service_running"]
    assert "observation_readiness_passed_with_engineering_blockers" in (
        validate_unattended_observation_readiness(payload)
    )
