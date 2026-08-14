import subprocess
from types import SimpleNamespace

from scripts import run_paper_operational_cycle
from scripts.run_paper_operational_cycle import _rs10_idle_wait_bridge_ready


def _certified_inputs(status: str) -> dict:
    return {
        "settings": SimpleNamespace(mode="paper", live_capital_enabled=False),
        "rs10": {
            "final_paper_autonomy_certified": True,
            "guarded_paper_autonomy_allowed": True,
            "certification_blocker_count": 0,
            "safety_blocker_count": 0,
            "live_capital_enabled": False,
        },
        "active_paper_automation": {
            "paperops_active_automation_status": status,
            "paperops_active_automation_submit_step_allowed": "False",
            "paperops_active_automation_poll_step_allowed": "False",
            "paperops_active_automation_exit_step_allowed": "False",
        },
        "qualified_setup_production": {
            "paperops_qualified_setup_qualified_setup_count": "0"
        },
        "paper_live_certification": {
            "paper_live_certification_status": "paper_live_certified",
            "paper_live_certification_unattended_delegation_enabled": "True",
        },
        "unsafe_counter_total": 0,
    }


def test_monitoring_bridge_accepts_safe_open_position_exit_state() -> None:
    inputs = _certified_inputs("active_automation_ready_to_exit")
    inputs["active_paper_automation"][
        "paperops_active_automation_exit_step_allowed"
    ] = "True"

    assert _rs10_idle_wait_bridge_ready(**inputs) is True


def test_monitoring_bridge_rejects_submit_authority_without_candidate() -> None:
    inputs = _certified_inputs("active_automation_ready_to_exit")
    inputs["active_paper_automation"][
        "paperops_active_automation_exit_step_allowed"
    ] = "True"
    inputs["active_paper_automation"][
        "paperops_active_automation_submit_step_allowed"
    ] = "True"

    assert _rs10_idle_wait_bridge_ready(**inputs) is False


def test_cockpit_timeout_is_bounded_and_reported_without_crashing(monkeypatch) -> None:
    def timeout_run(*_args, **kwargs):
        assert kwargs["timeout"] == 300
        raise subprocess.TimeoutExpired(
            cmd=["python", "scripts/check_cockpit_status.py"],
            timeout=kwargs["timeout"],
            output="partial=1\n",
            stderr="projection lock still held\n",
        )

    monkeypatch.setattr(run_paper_operational_cycle.subprocess, "run", timeout_run)

    result = run_paper_operational_cycle._run_command(
        "cockpit_status_pre_certification",
        "scripts/check_cockpit_status.py",
    )

    assert result["ok"] is False
    assert result["timed_out"] is True
    assert result["returncode"] == 124
    assert result["timeout_seconds"] == 300
    assert result["parsed"] == {"partial": "1"}
    assert result["stderr_tail"] == ["projection lock still held"]
