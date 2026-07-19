from __future__ import annotations

from orchestrator.qadam_guarded_paper_launch import build_release_approval


def test_release_approval_fails_closed_when_readiness_is_blocked() -> None:
    approval = build_release_approval(
        {
            "launch_ready": False,
            "paper_epoch_id": None,
            "version_refs": {},
            "blockers": ["no_validated_edge_available"],
        },
        approval_requested=True,
    )
    assert approval["operator_approved"] is False
    assert approval["approval_rejected_by_safety_gates"] is True
    assert approval["live_capital_release"] is False


def test_no_request_cannot_create_approval() -> None:
    approval = build_release_approval(
        {
            "launch_ready": True,
            "paper_epoch_id": "paper-epoch:test",
            "version_refs": {},
            "blockers": [],
        },
        approval_requested=False,
    )
    assert approval["operator_approved"] is False
    assert approval["paper_only_release"] is False
