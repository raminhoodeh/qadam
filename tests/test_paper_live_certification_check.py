from __future__ import annotations

from scripts.check_paper_live_certification import (
    _paper_live_submission_delegation_error,
)


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
