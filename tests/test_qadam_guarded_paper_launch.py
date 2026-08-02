from __future__ import annotations

from orchestrator.qadam_experimental_paper_policy import POLICY_VERSION
from orchestrator.qadam_guarded_paper_launch import (
    build_experimental_release_approval,
    build_release_approval,
    refresh_experimental_trial_calendar,
    validate_experimental_release_approval,
)


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


def _experimental_readiness() -> dict:
    return {
        "experimental_paper_release_ready": True,
        "paper_epoch_id": "paper-epoch:experimental",
        "policy_version": POLICY_VERSION,
        "risk_policy_version": "qadam-paper-portfolio-risk.3-frozen-discovery-5k",
        "binding_digest": "sha256:test-binding",
        "blockers": [],
    }


def test_experimental_release_approval_is_bound_and_expires() -> None:
    readiness = _experimental_readiness()
    approval = build_experimental_release_approval(
        readiness,
        approval_requested=True,
        approved_at="2026-07-19T00:00:00+00:00",
    )
    assert validate_experimental_release_approval(
        approval,
        readiness,
        observed_at="2026-07-19T00:14:59+00:00",
    ) == []
    assert "experimental_paper_release_approval_expired" in (
        validate_experimental_release_approval(
            approval,
            readiness,
            observed_at="2026-07-19T00:15:00+00:00",
        )
    )


def test_experimental_release_approval_rejects_rebinding_and_live_capital() -> None:
    readiness = _experimental_readiness()
    approval = build_experimental_release_approval(
        readiness,
        approval_requested=True,
        approved_at="2026-07-19T00:00:00+00:00",
    )
    approval["live_capital_release"] = True
    changed = {**readiness, "binding_digest": "sha256:changed"}
    errors = validate_experimental_release_approval(
        approval,
        changed,
        observed_at="2026-07-19T00:01:00+00:00",
    )
    assert "experimental_paper_release_approval_binding_changed" in errors
    assert "experimental_paper_release_approval_enabled_live_capital" in errors


def test_trial_calendar_uses_real_utc_dates_without_backfill(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        "orchestrator.qadam_guarded_paper_launch.runtime_dir",
        lambda _settings=None: tmp_path,
    )
    (tmp_path / "qadam_paper_trial_calendar.json").write_text(
        """{
  "trial_started_at": "2026-07-19T23:59:00+00:00",
  "trial_day": 1,
  "backfill_used": false,
  "simulated_elapsed_time_used": false
}\n""",
        encoding="utf-8",
    )
    calendar = refresh_experimental_trial_calendar(
        observed_at="2026-07-20T00:01:00+00:00"
    )
    assert calendar["trial_day"] == 2
    assert calendar["completed_calendar_day_count"] == 1
    assert calendar["backfill_used"] is False
    assert calendar["simulated_elapsed_time_used"] is False
