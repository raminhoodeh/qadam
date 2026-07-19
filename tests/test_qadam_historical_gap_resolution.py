from __future__ import annotations

from orchestrator.qadam_historical_gap_resolution import (
    _resolution_state,
    validate_historical_gap_resolution,
)


def test_provider_alignment_supersedes_without_backfilling_legacy_row() -> None:
    state, explanation, repairable = _resolution_state(
        {
            "typed_state": "price_history_absent",
            "source_key": "fred",
            "instrument": "SPY",
        },
        {
            ("fred", "SPY"): {
                "alignment_record_count": 100,
                "eligible_forward_window_count": 600,
            }
        },
    )
    assert state == "superseded_by_provider_alignment"
    assert "provider-backed" in explanation
    assert repairable is False


def test_unknown_gap_fails_closed_as_repairable() -> None:
    state, _explanation, repairable = _resolution_state(
        {"typed_state": "new_unknown_state", "source_key": "x", "instrument": "Y"},
        {},
    )
    assert state == "review_required_unclassified"
    assert repairable is True


def test_validation_accepts_safe_no_edge_outcome() -> None:
    authority = {
        "paper_only": True,
        "read_only": True,
        "proposal_first": True,
        "command_disabled": True,
        "live_capital_enabled": False,
        "live_broker_endpoint_allowed": False,
        "broker_write_allowed": False,
        "broker_write_count": 0,
        "paper_order_allowed": False,
        "paper_order_created": False,
        "paper_order_created_count": 0,
        "proof_credit_allowed": False,
        "paper_proof_ledger_credit_allowed": False,
        "qualified_setup_created": False,
        "trade_candidate_created": False,
        "trade_candidate_creation_allowed": False,
        "risk_approval_allowed": False,
        "risk_approval_created": False,
        "execution_approval_allowed": False,
        "execution_approval_created": False,
        "paper_growth_trial_calendar_advance_allowed": False,
        "simulated_elapsed_time_allowed": False,
        "telegram_command_path_enabled": False,
        "telegram_trade_command_enabled": False,
        "telegram_live_send_allowed": False,
        "policy_mutation_allowed": False,
        "autonomous_code_edit_allowed": False,
    }
    state = {
        "resolution": {
            "provider_partition_state": {
                "all_terminal": True,
                "remaining": 0,
                "acquired": 223,
                "classified_unavailable": 137,
                "total": 360,
            },
            "legacy_grid_state": {
                "record_count": 6232,
                "typed_record_count": 6232,
                "legacy_rows_mutated_or_backfilled": 0,
                "repairable_in_current_frozen_baseline_count": 0,
            },
            "authority": authority,
        },
        "registry": {"synthetic_completion_allowed": False, "authority": authority},
        "negative_controls": {"status": "passed", "authority": authority},
        "recertification": {
            "research_protocol_valid": True,
            "leakage_violation_count": 0,
            "holdout_tuning_violation_count": 0,
            "validated_edge_count": 0,
            "authority": authority,
        },
    }
    assert validate_historical_gap_resolution(state) == []
