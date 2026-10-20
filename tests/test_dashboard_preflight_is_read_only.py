from pathlib import Path


def test_dashboard_preflight_never_runs_mutating_paperops_wrapper() -> None:
    script = Path("scripts/preflight_dashboard_deployment.sh").read_text(encoding="utf-8")
    assert "scripts/run_paperops_autonomous_pass.py --report-only" in script
    assert '"$PYTHON_BIN" scripts/run_paperops_autonomous_pass.py\n' not in script
    assert "--live" not in script
    assert "run_qadam_maintenance_guard" not in script
    assert "check_qsase_dashboard_view_model.py" not in script
    assert "verify_dashboard_release_readonly.py" in script
