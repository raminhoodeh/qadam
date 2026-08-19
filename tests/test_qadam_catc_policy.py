from __future__ import annotations

from orchestrator.qadam_catc_release_reproducibility import (
    validate_release_reproducibility,
)
from orchestrator.qadam_gate_policy import evaluate_gate_inputs, hard_gate_failures
from orchestrator.qadam_primary_blocker import choose_primary_blocker


def test_missing_soft_evidence_reduces_size_without_hard_failure() -> None:
    measurements = {
        "paper_only_route": True,
        "live_capital_disabled": True,
        "provider_backed_current_trigger": True,
        "deterministic_direction": True,
        "paperable_proxy": True,
        "market_session_open": True,
        "actionable_quote": True,
        "positive_net_expectancy": True,
        "clear_invalidation": True,
        "risk_budget_available": True,
        "daily_drawdown_clear": True,
        "duplicate_exposure_clear": True,
        "idempotency_clear": True,
        "qctrl_hold_clear": True,
        "technical_confirmation": None,
        "volume_or_flow_confirmation": True,
        "nonlinear_quantum_review": None,
        "secondary_source_confirmation": True,
    }
    decisions, multiplier = evaluate_gate_inputs(
        "discovery_micro", measurements, decision_id="decision-1"
    )
    assert hard_gate_failures(decisions) == []
    assert 0.2 <= multiplier < 1.0


def test_market_closed_is_primary_over_dependent_missing_quote() -> None:
    blocker = choose_primary_blocker(
        [
            {
                "blocker_code": "actionable_quote_missing",
                "blocker_class": "provider",
                "summary": "No quote",
                "retryable": True,
            },
            {
                "blocker_code": "market_closed",
                "blocker_class": "market_session",
                "summary": "Market closed",
                "retryable": True,
            },
        ]
    )
    assert blocker is not None
    assert blocker.blocker_code == "market_closed"
    assert blocker.dependent_consequences == ("actionable_quote_missing",)


def test_release_reproducibility_requires_clean_bound_active_install() -> None:
    valid = validate_release_reproducibility(
        build_identity={"git_commit": "abc", "dirty_worktree": False},
        dashboard_audit={"protected_ux_preserved": True},
        runtime_owner={"active": True},
        launchd_template_matches=True,
    )
    assert valid == []

    blocked = validate_release_reproducibility(
        build_identity={"git_commit": "abc", "dirty_worktree": True},
        dashboard_audit={"protected_ux_preserved": False},
        runtime_owner={"active": False},
        launchd_template_matches=False,
    )
    assert set(blocked) == {
        "operator_build_scope_dirty",
        "protected_dashboard_ux_changed",
        "installed_launchd_template_mismatch",
        "guarded_paperops_runtime_owner_inactive",
    }
