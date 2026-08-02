from __future__ import annotations

import json
from pathlib import Path

from orchestrator import qadam_guarded_paper_launch as launch
from orchestrator.qadam_experimental_paper_policy import default_policy
from orchestrator.qadam_experimental_policy_amendment import build_policy_amendment
from orchestrator.qadam_operator_ready_common import file_sha256


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_current_policies(path: Path) -> None:
    _write(path / launch.EXPERIMENTAL_POLICY_ARTIFACT, default_policy())
    _write(
        path / "qadam_portfolio_policy.json",
        {"policy_version": launch.PORTFOLIO_RISK_POLICY_VERSION},
    )


def test_executed_release_remains_effective_when_status_is_rechecked(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(launch, "runtime_dir", lambda settings=None: tmp_path)
    _write_current_policies(tmp_path)
    epoch_id = "paper-epoch:test"
    _write(
        tmp_path / launch.RECEIPT_ARTIFACT,
        {
            "launch_executed": True,
            "experimental_mode": True,
            "canonical_wrapper": launch.CANONICAL_WRAPPER,
            "canonical_wrapper_returncode": 0,
            "direct_broker_call_count": 0,
            "paper_epoch_id": epoch_id,
            "trial_started_at": "2026-07-19T15:20:35+00:00",
        },
    )
    _write(
        tmp_path / launch.EXPERIMENTAL_READINESS_ARTIFACT,
        {
            "status": "blocked",
            "experimental_paper_release_effective": False,
            "blockers": [
                "paper_trial_already_started_before_release",
                "research_lock_not_active_before_experimental_release",
            ],
        },
    )
    _write(
        tmp_path / launch.EXPERIMENTAL_APPROVAL_ARTIFACT,
        {
            "experimental_paper_mandate_approved": True,
            "experimental_policy_operator_approved": True,
            "experimental_risk_policy_operator_approved": True,
            "paper_epoch_id": epoch_id,
            "policy_version": launch.EXPERIMENTAL_POLICY_VERSION,
            "live_capital_release": False,
        },
    )
    _write(
        tmp_path / launch.EPOCH_ARTIFACT,
        {
            "paper_epoch_id": epoch_id,
            "paper_epoch_kind": "clean_experimental_operator_epoch",
            "paper_growth_trial_calendar_started": True,
            "experimental_paper_release_policy_version": launch.EXPERIMENTAL_POLICY_VERSION,
        },
    )
    _write(
        tmp_path / launch.LOCK_ARTIFACT,
        {
            "status": "released",
            "paperops_watch_only_mode": False,
            "release_mode": "explicit_operator_approved_experimental_paper_epoch",
        },
    )
    _write(
        tmp_path / launch.TRIAL_CALENDAR_ARTIFACT,
        {
            "paper_epoch_id": epoch_id,
            "status": "active_real_calendar",
            "backfill_used": False,
            "simulated_elapsed_time_used": False,
        },
    )

    state = launch.build_current_experimental_release_state()

    assert state["status"] == "experimental_paper_release_effective"
    assert state["experimental_paper_release_effective"] is True
    assert state["blockers"] == []
    assert state["release_started_at"] == "2026-07-19T15:20:35+00:00"


def test_executed_release_fails_closed_when_epoch_binding_changes(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(launch, "runtime_dir", lambda settings=None: tmp_path)
    _write_current_policies(tmp_path)
    _write(
        tmp_path / launch.RECEIPT_ARTIFACT,
        {
            "launch_executed": True,
            "experimental_mode": True,
            "canonical_wrapper": launch.CANONICAL_WRAPPER,
            "canonical_wrapper_returncode": 0,
            "direct_broker_call_count": 0,
            "paper_epoch_id": "paper-epoch:old",
        },
    )
    _write(tmp_path / launch.EXPERIMENTAL_READINESS_ARTIFACT, {})
    _write(
        tmp_path / launch.EXPERIMENTAL_APPROVAL_ARTIFACT,
        {
            "experimental_paper_mandate_approved": True,
            "experimental_policy_operator_approved": True,
            "experimental_risk_policy_operator_approved": True,
            "paper_epoch_id": "paper-epoch:new",
            "policy_version": launch.EXPERIMENTAL_POLICY_VERSION,
            "live_capital_release": False,
        },
    )
    _write(
        tmp_path / launch.EPOCH_ARTIFACT,
        {
            "paper_epoch_id": "paper-epoch:new",
            "paper_epoch_kind": "clean_experimental_operator_epoch",
            "paper_growth_trial_calendar_started": True,
            "experimental_paper_release_policy_version": launch.EXPERIMENTAL_POLICY_VERSION,
        },
    )
    _write(
        tmp_path / launch.LOCK_ARTIFACT,
        {
            "status": "released",
            "paperops_watch_only_mode": False,
            "release_mode": "explicit_operator_approved_experimental_paper_epoch",
        },
    )
    _write(
        tmp_path / launch.TRIAL_CALENDAR_ARTIFACT,
        {
            "paper_epoch_id": "paper-epoch:new",
            "status": "active_real_calendar",
            "backfill_used": False,
            "simulated_elapsed_time_used": False,
        },
    )

    state = launch.build_current_experimental_release_state()

    assert state["experimental_paper_release_effective"] is False
    assert "experimental_release_receipt_epoch_mismatch" in state["blockers"]


def test_executed_release_accepts_a_bound_policy_amendment_without_resetting_time(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(launch, "runtime_dir", lambda settings=None: tmp_path)
    _write_current_policies(tmp_path)
    epoch_id = "paper-epoch:test"
    started_at = "2026-07-19T15:20:35+00:00"
    old_version = "qadam-experimental-paper.1-frozen"
    receipt = {
        "launch_executed": True,
        "experimental_mode": True,
        "canonical_wrapper": launch.CANONICAL_WRAPPER,
        "canonical_wrapper_returncode": 0,
        "direct_broker_call_count": 0,
        "paper_epoch_id": epoch_id,
        "trial_started_at": started_at,
    }
    approval = {
        "experimental_paper_mandate_approved": True,
        "experimental_policy_operator_approved": True,
        "experimental_risk_policy_operator_approved": True,
        "paper_epoch_id": epoch_id,
        "policy_version": old_version,
        "live_capital_release": False,
    }
    epoch = {
        "paper_epoch_id": epoch_id,
        "paper_epoch_kind": "clean_experimental_operator_epoch",
        "paper_growth_trial_calendar_started": True,
        "paper_growth_trial_started_at": started_at,
        "experimental_paper_release_policy_version": old_version,
    }
    calendar = {
        "paper_epoch_id": epoch_id,
        "status": "active_real_calendar",
        "trial_started_at": started_at,
        "backfill_used": False,
        "simulated_elapsed_time_used": False,
    }
    policy = default_policy("2026-08-02T00:00:00+00:00")
    _write(tmp_path / launch.RECEIPT_ARTIFACT, receipt)
    _write(tmp_path / launch.EXPERIMENTAL_READINESS_ARTIFACT, {})
    _write(tmp_path / launch.EXPERIMENTAL_APPROVAL_ARTIFACT, approval)
    _write(tmp_path / launch.EPOCH_ARTIFACT, epoch)
    _write(tmp_path / launch.TRIAL_CALENDAR_ARTIFACT, calendar)
    _write(tmp_path / launch.EXPERIMENTAL_POLICY_ARTIFACT, policy)
    _write(
        tmp_path / launch.LOCK_ARTIFACT,
        {
            "status": "released",
            "paperops_watch_only_mode": False,
            "release_mode": "explicit_operator_approved_experimental_paper_epoch",
        },
    )
    amendment = build_policy_amendment(
        previous_policy={"policy_version": old_version},
        amended_policy=policy,
        release_approval=approval,
        paper_epoch=epoch,
        trial_calendar=calendar,
        previous_approval_sha256=file_sha256(
            tmp_path / launch.EXPERIMENTAL_APPROVAL_ARTIFACT
        ),
        explicit_operator_approval=True,
        generated_at="2026-08-02T00:00:00+00:00",
    )
    _write(tmp_path / launch.EXPERIMENTAL_POLICY_AMENDMENT_ARTIFACT, amendment)

    state = launch.build_current_experimental_release_state()

    assert state["experimental_paper_release_effective"] is True
    assert state["policy_amendment_effective"] is True
    assert state["launch_policy_version"] == old_version
    assert state["policy_version"] == launch.EXPERIMENTAL_POLICY_VERSION
    assert state["release_started_at"] == started_at
