from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone

from orchestrator.qadam_autonomous_experimental_paper_epoch import (
    PROTECTED_DASHBOARD_APPROVED_COMMIT,
    _dashboard_hash_audit,
    _operation_gates,
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
        "a92ea992a4648dd819149c497a2797fc4551b95c"
    )
    assert audit["matching_asset_count"] == audit["asset_count"] == 4
    assert audit["protected_ux_preserved"] is True


def test_running_epoch_uses_durable_account_binding_not_empty_account_state(
    tmp_path, monkeypatch
) -> None:
    generated_at = datetime.now(timezone.utc).isoformat()
    fingerprint = "sha256:current-account"
    artifacts = {
        "qadam_clean_broker_account_preflight.json": {
            "paper_endpoint_verified": True,
            "preflight_passed": False,
            "position_count": 1,
            "order_count": 3,
        },
        "alpaca_paper_mirror.json": {
            "status": "ok",
            "broker_account_fingerprint": fingerprint,
            "broker_reconciliation_status": "ok",
            "paper_epoch_id": "epoch-current",
            "paper_epoch_kind": "clean_experimental_operator_epoch",
            "position_count": 1,
            "order_count": 3,
            "snapshot": {
                "observed_at": generated_at,
                "account_currency": "USD",
                "equity": 101250.0,
            },
        },
        "current_paper_epoch.json": {
            "paper_epoch_id": "epoch-current",
            "paper_epoch_kind": "clean_experimental_operator_epoch",
            "starting_balance": 100000.0,
            "account_currency": "USD",
            "broker_account_fingerprint": fingerprint,
        },
        "qadam_clean_epoch_cutover_receipt.json": {
            "cutover_executed": True,
            "cutover_mode": "experimental_unvalidated",
            "testing_epoch_archived": True,
            "provider_backed_initial_mirror": True,
            "starting_balance": 100000.0,
            "paper_epoch_id": "epoch-current",
            "broker_account_fingerprint": fingerprint,
            "status": "experimental_cutover_complete_watch_only",
        },
    }
    for name, payload in artifacts.items():
        (tmp_path / name).write_text(json.dumps(payload))

    monkeypatch.setattr(
        "orchestrator.qadam_autonomous_experimental_paper_epoch.read_json",
        lambda path: json.loads(path.read_text()) if path.exists() else {},
    )
    gates = _operation_gates(tmp_path)
    account_gate = next(
        row
        for row in gates
        if row["gate_id"] == "active_bound_100000_usd_alpaca_paper_epoch"
    )

    assert account_gate["passed"] is True
    assert account_gate["observed"]["positions"] == 1
    assert account_gate["observed"]["orders"] == 3
