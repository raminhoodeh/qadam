from scripts.check_cockpit_status import _canonical_paper_runtime_ready


def _canonical_runtime() -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    rs10: dict[str, object] = {
        "status": "certified_actionable",
        "final_paper_autonomy_certified": True,
        "guarded_paper_autonomy_allowed": True,
        "certification_blocker_count": 0,
        "safety_blocker_count": 0,
        "stale_blocker_in_current_count": 0,
        "live_capital_enabled": False,
        "unsafe_write_counter_total": 0,
    }
    paper_live: dict[str, object] = {
        "status": "paper_live_certified",
        "paper_live_control_plane_certified": True,
        "paper_live_certified": True,
        "paper_live_operation_allowed": True,
        "paper_live_unattended_execution_delegation_enabled": True,
        "certification_blocker_count": 0,
        "control_plane_blocker_count": 0,
        "live_capital_enabled": False,
        "unsafe_write_counter_total": 0,
    }
    active: dict[str, object] = {
        "status": "active_automation_ready_to_submit",
        "active_paper_trading_automation_enabled": True,
        "active_paper_trading_automation_effective": True,
        "automation_active": True,
        "unattended_paper_execution_delegation_enabled": True,
        "paper_endpoint_confirmed": True,
        "blocker_count": 0,
        "validation_error_count": 0,
        "direct_broker_shortcut_allowed": False,
        "forced_trades_allowed": False,
        "live_capital_enabled": False,
        "unsafe_write_counter_total": 0,
    }
    return rs10, paper_live, active


def test_canonical_runtime_supersedes_retired_readiness_authority() -> None:
    assert _canonical_paper_runtime_ready(*_canonical_runtime()) is True


def test_canonical_runtime_fails_closed_on_live_capital_or_blockers() -> None:
    rs10, paper_live, active = _canonical_runtime()
    rs10["live_capital_enabled"] = True
    assert _canonical_paper_runtime_ready(rs10, paper_live, active) is False

    rs10, paper_live, active = _canonical_runtime()
    paper_live["certification_blocker_count"] = 1
    assert _canonical_paper_runtime_ready(rs10, paper_live, active) is False


def test_canonical_runtime_requires_the_single_active_execution_owner() -> None:
    rs10, paper_live, active = _canonical_runtime()
    active["status"] = "blocked_active_automation_safety_or_binding"
    assert _canonical_paper_runtime_ready(rs10, paper_live, active) is False

    active["status"] = "active_automation_ready_to_submit"
    active["direct_broker_shortcut_allowed"] = True
    assert _canonical_paper_runtime_ready(rs10, paper_live, active) is False
