from __future__ import annotations

from scripts.check_paper_live_certification import (
    _legacy_phase7_milestone_errors,
    _paper_live_submission_delegation_error,
)
from orchestrator.paper_live_certification import _apply_rs10_bridge_to_gates


def _artifact(
    *,
    certified: bool = True,
    submit_step_allowed: bool = False,
    qctrl_hold_active: bool = False,
    submission_delegation_allowed: bool = False,
) -> dict:
    return {
        "paper_live_certified": certified,
        "paper_submit_step_allowed": submit_step_allowed,
        "qctrl_hold_active": qctrl_hold_active,
        "paper_live_submission_delegation_allowed": submission_delegation_allowed,
    }


def test_submission_delegation_can_stay_false_while_certified_idle() -> None:
    assert _paper_live_submission_delegation_error(_artifact()) is None


def test_submission_delegation_required_for_fresh_actionable_submit() -> None:
    assert (
        _paper_live_submission_delegation_error(
            _artifact(submit_step_allowed=True, submission_delegation_allowed=False)
        )
        == "paper_live_submission_delegation_not_enabled"
    )
    assert (
        _paper_live_submission_delegation_error(
            _artifact(submit_step_allowed=True, submission_delegation_allowed=True)
        )
        is None
    )


def test_submission_delegation_rejected_when_no_submit_is_actionable() -> None:
    assert (
        _paper_live_submission_delegation_error(
            _artifact(submit_step_allowed=False, submission_delegation_allowed=True)
        )
        == "paper_live_submission_unexpectedly_delegated"
    )


def test_completed_legacy_calendar_without_proof_is_observation_not_failure() -> None:
    assert (
        _legacy_phase7_milestone_errors(
            {
                "phase7_30_day_run_complete": True,
                "phase7_demo_proof_certified": False,
                "phase7_proof_credit_allowed": False,
            }
        )
        == []
    )


def test_rs10_bridge_supersedes_legacy_cockpit_gate() -> None:
    gates = [
        {
            "key": "pt9_cockpit_notification_ready",
            "required_for_control_plane": True,
            "required_for_paper_live_certification": True,
            "passed": False,
            "detail": "Legacy cockpit projection is stale.",
        }
    ]

    bridged = _apply_rs10_bridge_to_gates(
        gate_records=gates,
        rs10_bridge_ready=True,
        rs10_status="certified_actionable",
    )

    legacy = bridged[0]
    assert legacy["required_for_control_plane"] is False
    assert legacy["required_for_paper_live_certification"] is False
    assert legacy["superseded_by_rs10_final_paper_autonomy"] is True
    assert bridged[-1]["key"] == "rs10_final_paper_autonomy_certified"


def test_legacy_cockpit_gate_still_blocks_without_rs10_bridge() -> None:
    gates = [
        {
            "key": "pt9_cockpit_notification_ready",
            "required_for_control_plane": True,
            "required_for_paper_live_certification": True,
            "passed": False,
            "detail": "Legacy cockpit projection is stale.",
        }
    ]

    unchanged = _apply_rs10_bridge_to_gates(
        gate_records=gates,
        rs10_bridge_ready=False,
        rs10_status="blocked",
    )

    assert unchanged == gates
