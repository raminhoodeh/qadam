from types import SimpleNamespace

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
