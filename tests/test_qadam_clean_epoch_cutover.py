from __future__ import annotations

import pytest

from orchestrator.qadam_clean_epoch_cutover import execute_clean_epoch_cutover


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
