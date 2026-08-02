from __future__ import annotations

import pytest

from orchestrator.qadam_experimental_paper_policy import POLICY_VERSION
from orchestrator.qadam_clean_epoch_cutover import (
    execute_clean_epoch_cutover,
    execute_experimental_epoch_cutover,
    validate_experimental_epoch_cutover_approval,
)


def test_cutover_requires_explicit_operator_approval() -> None:
    with pytest.raises(PermissionError, match="explicit clean-epoch"):
        execute_clean_epoch_cutover(operator_approved=False)


def test_cutover_refuses_when_readiness_is_blocked(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        "orchestrator.qadam_clean_epoch_cutover.runtime_dir", lambda _settings=None: tmp_path
    )
    monkeypatch.setattr(
        "orchestrator.qadam_clean_epoch_cutover.build_clean_epoch_cutover_readiness",
        lambda _settings=None, require_service_paused=False: {
            "cutover_ready": False,
            "blockers": ["validated_edge_gate_not_passed"],
        },
    )
    with pytest.raises(RuntimeError, match="validated_edge_gate_not_passed"):
        execute_clean_epoch_cutover(operator_approved=True)
    assert not (tmp_path / ".qadam-clean-epoch-cutover.lock").exists()


def test_experimental_cutover_requires_explicit_operator_approval() -> None:
    with pytest.raises(PermissionError, match="experimental clean-epoch"):
        execute_experimental_epoch_cutover(operator_approved=False)


def test_experimental_cutover_approval_rejects_expiry_and_binding_change() -> None:
    readiness = {
        "binding_digest": "sha256:current",
    }
    approval = {
        "operator_approved": True,
        "expires_at": "2000-01-01T00:00:00+00:00",
        "binding_digest": "sha256:old",
        "policy_version": POLICY_VERSION,
        "live_capital_enabled": False,
    }
    errors = validate_experimental_epoch_cutover_approval(approval, readiness)
    assert "experimental_cutover_approval_expired" in errors
    assert "experimental_cutover_approval_binding_changed" in errors


def test_experimental_cutover_approval_rejects_live_capital() -> None:
    approval = {
        "operator_approved": True,
        "expires_at": "2999-01-01T00:00:00+00:00",
        "binding_digest": "sha256:current",
        "policy_version": POLICY_VERSION,
        "live_capital_enabled": True,
    }
    errors = validate_experimental_epoch_cutover_approval(
        approval,
        {"binding_digest": "sha256:current"},
    )
    assert "experimental_cutover_approval_enabled_live_capital" in errors
