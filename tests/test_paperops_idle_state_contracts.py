from __future__ import annotations

from copy import deepcopy

from orchestrator.paperops_autonomous_pass import (
    validate_paperops_autonomous_pass_summary,
)
from scripts.check_paperops_paper_exit_path import _safe_idle_without_exposure


def test_zero_exposure_exit_path_is_safe_idle() -> None:
    written = {
        "status": "disabled_pending_enablement",
        "source_paperops_3_status": "ready_no_submitted_paper_orders",
        "endpoint_classification": "alpaca_paper_endpoint",
        "paper_endpoint_confirmed": True,
        "alpaca_api_key_configured": True,
        "alpaca_api_secret_configured": True,
        "live_capital_enabled": False,
        "open_position_readback_count": 0,
        "eligible_exit_record_count": 0,
        "paper_position_close_called_count": 0,
        "broker_write_called_count": 0,
        "live_endpoint_called_count": 0,
    }
    preview = {
        "status": "ready_no_exit_candidate",
        "execute_exit_requested": False,
        "paper_position_close_called_count": 0,
    }

    assert _safe_idle_without_exposure(written, preview) is True

    unsafe = deepcopy(written)
    unsafe["open_position_readback_count"] = 1
    assert _safe_idle_without_exposure(unsafe, preview) is False


def test_router_no_handoff_is_a_valid_canonical_idle_reason() -> None:
    summary = {
        "schema_version": 1,
        "artifact_type": "paperops_autonomous_pass_summary",
        "public_safe": True,
        "status": "ready_idle",
        "paper_growth_trial": {"run_day": 1},
        "paper_proof_ledger": {},
        "paper_runtime": {
            "fresh_eligible_submit_count": 0,
            "duplicate_submit_count": 0,
            "submitted_paper_order_count": 0,
            "idle_reason": "router_v3_no_accepted_handoff",
        },
        "states": {
            "active_automation_state": "active_automation_enabled_idle",
            "paper_ops_cycle_contract_check": "ok",
            "paper_ops_cycle_state": "paper_cycle_full_paper_operational_ready",
        },
        "safety": {
            "live_capital_enabled": False,
            "phase7_proof_credit_allowed": False,
            "broker_post_called_count": 0,
            "alpaca_post_called_count": 0,
            "notification_live_send_allowed_count": 0,
            "command_path_enabled_count": 0,
        },
        "blockers": [],
        "blocker_count": 0,
        "optional_gaps": [],
        "optional_gap_count": 0,
        "source_gap_visibility": {},
        "edge_pattern_ledger": {},
        "closed_trade_funnel": {},
        "close_to_ledger": {},
        "submit_regression_guard": {},
        "router_v3_handoff_boundary": {
            "new_paper_submission_allowed": False,
            "accepted_handoff_count": 0,
        },
        "command_results": [],
        "automation_report_lines": [
            "30-day paper growth trial is ready.",
            "Paper proof ledger is unchanged.",
        ],
    }

    errors = validate_paperops_autonomous_pass_summary(summary)

    assert "paperops_autonomous_pass_missing_idle_reason" not in errors
