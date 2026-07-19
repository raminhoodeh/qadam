from __future__ import annotations

from orchestrator.qadam_experimental_paper_trial import (
    validate_experimental_paper_trial,
)
from orchestrator.qadam_operator_ready_common import authority_flags


def test_trial_rejects_calendar_fabrication_and_edge_credit() -> None:
    summary = {
        "paper_epoch_id": "epoch:test",
        "backfill_used": True,
        "simulated_elapsed_time_used": True,
        "validated_edge_evidence_count": 1,
        "validated_edge_credit_count": 1,
        "automatic_strategy_promotion_allowed": True,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }
    errors = validate_experimental_paper_trial(summary, [])
    assert "experimental_trial_calendar_backfilled" in errors
    assert "experimental_trial_simulated_elapsed_time" in errors
    assert "experimental_trial_granted_validated_edge_credit" in errors


def test_trial_outcome_cannot_claim_validated_edge_credit() -> None:
    summary = {
        "paper_epoch_id": "epoch:test",
        "backfill_used": False,
        "simulated_elapsed_time_used": False,
        "validated_edge_evidence_count": 0,
        "validated_edge_credit_count": 0,
        "automatic_strategy_promotion_allowed": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }
    outcomes = [
        {
            "paper_epoch_id": "epoch:test",
            "proof_tier": "experimental_forward_outcome",
            "validated_edge_credit": True,
            "authority": authority_flags(),
        }
    ]
    assert "experimental_trial_outcome_granted_edge_credit" in (
        validate_experimental_paper_trial(summary, outcomes)
    )
