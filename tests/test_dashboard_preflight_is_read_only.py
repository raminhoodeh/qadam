from pathlib import Path


def test_dashboard_preflight_never_runs_mutating_paperops_wrapper() -> None:
    script = Path("scripts/preflight_dashboard_deployment.sh").read_text(encoding="utf-8")
    assert "scripts/run_paperops_autonomous_pass.py --report-only" in script
    assert '"$PYTHON_BIN" scripts/run_paperops_autonomous_pass.py\n' not in script
