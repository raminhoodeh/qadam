from __future__ import annotations

from copy import deepcopy

from orchestrator.qadam_autonomous_experimental_paper_epoch import (
    PROTECTED_DASHBOARD_APPROVED_COMMIT,
    _dashboard_hash_audit,
    validate_autonomous_experimental_paper_epoch_certification,
)
from orchestrator.qadam_operator_ready_common import authority_flags


def _base() -> dict:
    return {
        "implementation_complete": True,
        "autonomous_experimental_paper_operation_running": False,
        "unattended_reliability_certified": False,
        "implementation_blockers": [],
        "operation_blockers": ["clean_account_missing"],
        "implementation_gates": [{"passed": True}],
        "negative_safety_probes": [{"passed": True}],
        "operation_gates": [{"passed": False}],
        "dashboard_ux_protection": {"protected_ux_preserved": True},
        "paper_only": True,
        "live_capital_enabled": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "paper_calendar_advanced_by_certifier": False,
        "authority": authority_flags(),
    }


def test_implementation_can_pass_while_real_broker_cutover_waits() -> None:
    assert validate_autonomous_experimental_paper_epoch_certification(_base()) == []


def test_operation_cannot_claim_running_with_failed_gate() -> None:
    payload = _base()
    payload["autonomous_experimental_paper_operation_running"] = True
    assert "operation_running_with_blockers" in (
        validate_autonomous_experimental_paper_epoch_certification(payload)
    )


def test_unattended_reliability_requires_running_operation() -> None:
    payload = _base()
    payload["unattended_reliability_certified"] = True
    assert "unattended_reliability_without_running_operation" in (
        validate_autonomous_experimental_paper_epoch_certification(payload)
    )


def test_live_capital_and_dashboard_drift_fail_closed() -> None:
    payload = deepcopy(_base())
    payload["live_capital_enabled"] = True
    payload["dashboard_ux_protection"]["protected_ux_preserved"] = False
    errors = validate_autonomous_experimental_paper_epoch_certification(payload)
    assert "certification_live_capital_enabled" in errors
    assert "protected_dashboard_ux_changed" in errors


def test_current_approved_dashboard_release_matches_frozen_ux() -> None:
    audit = _dashboard_hash_audit()

    assert PROTECTED_DASHBOARD_APPROVED_COMMIT == (
        "836584dc5b241fdc8176c54fef522ee583708a25"
    )
    assert audit["matching_asset_count"] == audit["asset_count"] == 4
    assert audit["protected_ux_preserved"] is True
