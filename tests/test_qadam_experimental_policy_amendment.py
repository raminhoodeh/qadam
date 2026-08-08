from __future__ import annotations

from copy import deepcopy

from orchestrator.qadam_experimental_paper_policy import default_policy
from orchestrator.qadam_experimental_policy_amendment import (
    build_policy_amendment,
    validate_policy_amendment,
)


def _inputs() -> tuple[dict, dict, dict, dict, dict]:
    previous_policy = {"policy_version": "qadam-experimental-paper.1-frozen"}
    amended_policy = default_policy("2026-08-02T00:00:00+00:00")
    approval = {
        "experimental_paper_mandate_approved": True,
        "live_capital_release": False,
        "paper_epoch_id": "paper-epoch:test",
        "policy_version": previous_policy["policy_version"],
    }
    epoch = {
        "paper_epoch_id": "paper-epoch:test",
        "experimental_paper_release_policy_version": previous_policy["policy_version"],
        "paper_growth_trial_started_at": "2026-07-19T15:20:35+00:00",
    }
    calendar = {
        "paper_epoch_id": "paper-epoch:test",
        "trial_started_at": "2026-07-19T15:20:35+00:00",
        "backfill_used": False,
        "simulated_elapsed_time_used": False,
    }
    return previous_policy, amended_policy, approval, epoch, calendar


def test_operator_approved_amendment_preserves_epoch_and_calendar() -> None:
    previous, policy, approval, epoch, calendar = _inputs()
    amendment = build_policy_amendment(
        previous_policy=previous,
        amended_policy=policy,
        release_approval=approval,
        paper_epoch=epoch,
        trial_calendar=calendar,
        previous_approval_sha256="approval-sha",
        explicit_operator_approval=True,
        generated_at="2026-08-02T00:00:00+00:00",
    )

    assert validate_policy_amendment(
        amendment,
        policy=policy,
        release_approval=approval,
        paper_epoch=epoch,
        trial_calendar=calendar,
        previous_approval_sha256="approval-sha",
    ) == []
    assert amendment["paper_trial_calendar_reset"] is False
    assert amendment["paper_order_created_count"] == 0
    assert amendment["broker_write_count"] == 0
    assert amendment["live_capital_enabled"] is False


def test_amendment_fails_closed_if_risk_or_calendar_binding_changes() -> None:
    previous, policy, approval, epoch, calendar = _inputs()
    amendment = build_policy_amendment(
        previous_policy=previous,
        amended_policy=policy,
        release_approval=approval,
        paper_epoch=epoch,
        trial_calendar=calendar,
        previous_approval_sha256="approval-sha",
        explicit_operator_approval=True,
    )
    changed_policy = deepcopy(policy)
    changed_policy["risk"]["discovery_micro_trade_ceiling_usd"] = 500.0
    changed_calendar = {**calendar, "trial_started_at": "2026-08-02T00:00:00+00:00"}

    errors = validate_policy_amendment(
        amendment,
        policy=changed_policy,
        release_approval=approval,
        paper_epoch=epoch,
        trial_calendar=changed_calendar,
        previous_approval_sha256="approval-sha",
    )

    assert "experimental_policy_amendment_binding_changed:trial_started_at" in errors
    assert "experimental_policy_amendment_binding_changed:discovery_micro_trade_ceiling_usd" in errors
    assert "experimental_policy_discovery_micro_ceiling_changed" in errors


def test_amendment_binds_the_evidence_adaptive_admission_contract() -> None:
    previous, policy, approval, epoch, calendar = _inputs()
    amendment = build_policy_amendment(
        previous_policy=previous,
        amended_policy=policy,
        release_approval=approval,
        paper_epoch=epoch,
        trial_calendar=calendar,
        previous_approval_sha256="approval-sha",
        explicit_operator_approval=True,
    )
    changed_policy = deepcopy(policy)
    changed_policy["discovery_micro_admission"][
        "source_quorum_eligible_required"
    ] = True

    errors = validate_policy_amendment(
        amendment,
        policy=changed_policy,
        release_approval=approval,
        paper_epoch=epoch,
        trial_calendar=calendar,
        previous_approval_sha256="approval-sha",
    )

    assert (
        "experimental_policy_amendment_binding_changed:discovery_micro_admission_digest"
        in errors
    )


def test_operator_can_supersede_an_existing_bound_amendment() -> None:
    previous, policy, approval, epoch, calendar = _inputs()
    previous_policy = {
        "policy_version": "qadam-experimental-paper.2-frozen-discovery-micro",
        "risk": {
            "portfolio_policy_version": "qadam-paper-portfolio-risk.2-frozen",
            "discovery_micro_trade_ceiling_usd": 500.0,
        },
    }
    previous_amendment = {
        "amendment_id": "experimental-policy-amendment:previous",
        "operator_approved": True,
        "from_policy_version": approval["policy_version"],
        "to_policy_version": previous_policy["policy_version"],
        "paper_epoch_id": epoch["paper_epoch_id"],
        "trial_started_at": calendar["trial_started_at"],
    }

    amendment = build_policy_amendment(
        previous_policy=previous_policy,
        amended_policy=policy,
        release_approval=approval,
        paper_epoch=epoch,
        trial_calendar=calendar,
        previous_approval_sha256="approval-sha",
        explicit_operator_approval=True,
        previous_amendment=previous_amendment,
        generated_at="2026-08-02T00:00:00+00:00",
    )

    assert validate_policy_amendment(
        amendment,
        policy=policy,
        release_approval=approval,
        paper_epoch=epoch,
        trial_calendar=calendar,
        previous_approval_sha256="approval-sha",
        policy_history=[previous_policy],
    ) == []
    assert amendment["supersedes_policy_version"] == previous_policy["policy_version"]
    assert amendment["supersedes_amendment_id"] == previous_amendment["amendment_id"]
    assert amendment["discovery_micro_trade_ceiling_usd"] == 5000.0
