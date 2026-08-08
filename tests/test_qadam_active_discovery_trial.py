from __future__ import annotations

from orchestrator.qadam_active_discovery_trial import (
    EVIDENCE_FIT_CONTRACT_VERSION,
    MARKET_SESSION_TARGET,
    PRIMARY_ROOT_CAUSES,
    TRIAL_VERSION,
    _primary_root_cause,
    validate_active_discovery_trial,
)
from orchestrator.qadam_experimental_paper_policy import POLICY_VERSION
from orchestrator.qadam_operator_ready_common import authority_flags


def _contract() -> dict:
    return {
        "trial_version": TRIAL_VERSION,
        "evidence_fit_contract_version": EVIDENCE_FIT_CONTRACT_VERSION,
        "market_session_target": MARKET_SESSION_TARGET,
        "expected_instrument_count": 19,
        "shortlist_target_per_session": 5,
        "seven_stages": [{"stage": value} for value in range(1, 8)],
        "acceptance_contract": {"trade_quota": None},
        "calendar": {"backfill_allowed": False, "simulated_elapsed_time_allowed": False},
        "boundaries": {
            "live_capital_enabled": False,
            "direct_broker_write_allowed": False,
            "automatic_ambiguous_write_retry_allowed": False,
            "validated_edge_credit_allowed": False,
            "paper_proof_ledger_credit_allowed": False,
            "thirty_day_trial_calendar_advance_allowed": False,
        },
        "frozen_policy": {
            "experimental_policy_version": POLICY_VERSION,
            "portfolio_policy_version": "qadam-paper-portfolio-risk.4-active-discovery-trial",
            "discovery_target_notional_usd": {"minimum": 500.0, "maximum": 1000.0},
            "absolute_trade_ceiling_usd": 5000.0,
            "maximum_concurrent_discovery_positions": 3,
            "maximum_discovery_positions_per_correlated_cluster": 1,
            "guarded_route": "guarded_alpaca_paper_via_paperops",
        },
        "policy_binding": {
            "policy_version": POLICY_VERSION,
            "policy_contract_digest": "sha256:policy",
            "amendment_id": "amendment:test",
            "amendment_generated_at": "2026-08-04T00:00:00+00:00",
            "amendment_to_policy_version": POLICY_VERSION,
            "operator_approved": True,
        },
        "calibration_snapshot": {
            "backtest_manifest_sha256": "sha256:backtest",
            "akber_replay_sha256": "sha256:replay",
            "akber_ablation_sha256": "sha256:ablation",
            "thresholds_frozen_during_trial": True,
            "automatic_recalibration_allowed": False,
        },
        "authority": authority_flags(),
    }


def test_trial_rejects_trade_quota_and_calendar_fabrication() -> None:
    contract = _contract()
    contract["acceptance_contract"]["trade_quota"] = 1
    contract["calendar"]["backfill_allowed"] = True
    errors = validate_active_discovery_trial(
        contract,
        {"paper_order_created_by_trial_module": 0, "authority": authority_flags()},
        [],
        [],
    )
    assert "active_discovery_trial_trade_quota_present" in errors
    assert "active_discovery_trial_calendar_fabrication_allowed" in errors


def test_evaluation_cannot_create_candidate_order_or_proof() -> None:
    evaluation = {
        "evaluation_id": "evaluation:test",
        "candidate_created": True,
        "order_created": True,
        "live_capital_enabled": False,
        "proof_credit_count": 1,
        "authority": authority_flags(),
    }
    errors = validate_active_discovery_trial(
        _contract(),
        {"paper_order_created_by_trial_module": 0, "authority": authority_flags()},
        [evaluation],
        [],
    )
    assert "active_discovery_evaluation_created_trade_object:evaluation:test" in errors
    assert "active_discovery_evaluation_unsafe:evaluation:test" in errors


def test_session_must_be_real_and_cannot_pressure_a_trade() -> None:
    session = {
        "session_id": "session:test",
        "backfilled": True,
        "simulated_elapsed_time": True,
        "forced_trade_allowed": True,
        "trade_quota": 1,
    }
    errors = validate_active_discovery_trial(
        _contract(),
        {"paper_order_created_by_trial_module": 0, "authority": authority_flags()},
        [],
        [session],
    )
    assert "active_discovery_session_not_real:session:test" in errors
    assert "active_discovery_session_trade_pressure:session:test" in errors


def test_no_trade_root_cause_prefers_inactive_trigger_over_downstream_noise() -> None:
    row = {
        "market_session_actionable": True,
        "current_trigger_state": "inactive",
        "akber_decision": "watchlist_inactive_trigger",
        "risk_state": "not_reached",
        "router_state": "watchlist",
        "blockers": ["risk_proposal_incomplete", "akber_pass_missing"],
    }
    assert _primary_root_cause(row) == "no_real_trigger"
    assert _primary_root_cause(row) in PRIMARY_ROOT_CAUSES


def test_real_trigger_missing_hypothesis_is_conversion_defect() -> None:
    row = {
        "market_session_actionable": True,
        "current_trigger_state": "active",
        "hypothesis_id": None,
        "akber_decision": "not_reached",
        "risk_state": "not_reached",
        "router_state": "not_reached",
        "blockers": ["decision_critical_pattern_features_missing"],
    }
    assert _primary_root_cause(row) == "evidence_conversion_defect"
