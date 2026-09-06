from importlib import import_module

import pytest


@pytest.mark.parametrize("old,new", [
    ("qadam_decision_transaction", "contracts.decision"),
    ("qadam_control_plane_store", "storage.control_plane"),
    ("qadam_operating_ledger", "execution.ledger"),
    ("qadam_outcome_attribution", "learning.attribution"),
    ("qadam_forward_evaluation", "learning.forward_evaluation"),
    ("qadam_forward_tournament", "learning.tournament"),
    ("qadam_strategy_foundry_v3", "research.foundry"),
    ("qadam_operator_service", "runtime.operator"),
    ("qsase_dashboard_view_model", "presentation.dashboard"),
    ("qadam_tradeability_pipeline", "decisions.pipeline"),
])
def test_old_import_is_same_implementation_not_another_owner(old, new):
    assert import_module("orchestrator." + old) is import_module("orchestrator." + new)


def test_execution_package_preserves_original_venue_registry():
    from orchestrator.execution import execution_registry
    from orchestrator.execution.venues import execution_registry as implementation
    assert execution_registry is implementation
    assert {row["key"] for row in execution_registry()} == {
        "alpaca_paper", "prediction_market_router", "privex_base", "privex_coti"}


def test_dashboard_resolves_repository_not_package_parent():
    from orchestrator.presentation.dashboard import _repo_root
    from orchestrator.qadam_operator_ready_common import ROOT
    assert _repo_root() == ROOT


def test_alternate_directory_cannot_create_a_second_default_state_root(tmp_path, monkeypatch):
    from pathlib import Path
    from orchestrator.config import Settings
    from orchestrator.paths import project_root
    root = project_root()
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("QADAM_RUNTIME_DIR", raising=False)
    assert Path(Settings.from_env().runtime_dir) == root / "data/runtime"
    assert not (tmp_path / "data").exists()


def test_explicit_resource_root_cannot_be_relative(monkeypatch):
    from orchestrator.paths import project_root
    monkeypatch.setenv("QADAM_PROJECT_ROOT", "./other")
    with pytest.raises(ValueError, match="must_be_absolute"):
        project_root()
