from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from orchestrator.config import Settings
from orchestrator.qadam_paperops_runtime_owner import (
    CANONICAL_WRAPPER,
    operator_service_automation_projection,
    paperops_runtime_owner_status,
)


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _settings(tmp_path: Path) -> Settings:
    return replace(
        Settings.from_env(),
        runtime_dir=str(tmp_path),
        mode="paper",
        live_capital_enabled=False,
    )


def _write_ready_runtime(tmp_path: Path) -> None:
    epoch_id = "paper-epoch:test"
    _write(
        tmp_path / "qadam_experimental_paper_release_readiness.json",
        {
            "status": "experimental_paper_release_effective",
            "experimental_paper_release_effective": True,
            "experimental_paper_release_ready": True,
            "canonical_wrapper": CANONICAL_WRAPPER,
            "paper_epoch_id": epoch_id,
            "blockers": [],
        },
    )
    _write(
        tmp_path / "current_paper_epoch.json",
        {
            "paper_epoch_id": epoch_id,
            "paper_epoch_kind": "clean_experimental_operator_epoch",
            "paper_growth_trial_calendar_started": True,
            "paper_growth_trial_state": "active_real_calendar",
            "paper_growth_trial_calendar_backfilled": False,
            "simulated_elapsed_time": False,
        },
    )
    _write(
        tmp_path / "qadam_long_backtest_lock.json",
        {
            "status": "released",
            "paperops_watch_only_mode": False,
            "release_mode": "explicit_operator_approved_experimental_paper_epoch",
            "release_approval_epoch_id": epoch_id,
        },
    )
    _write(
        tmp_path / "qadam_operator_service_status.json",
        {
            "service_installed": True,
            "service_running": True,
            "release_effective": True,
            "paperops_watch_only": False,
            "direct_broker_client_import_allowed": False,
            "liveness": {"process_running": True},
            "authority": {
                "paper_only": True,
                "live_capital_enabled": False,
                "live_broker_endpoint_allowed": False,
            },
            "services": [
                {
                    "service_id": "guarded_paperops",
                    "command_sequence": [
                        [".venv/bin/python", CANONICAL_WRAPPER]
                    ],
                    "ownership": "canonical_paperops_wrapper_only",
                    "safety_mode": "guarded_alpaca_paper_wrapper_only",
                    "paperops_dependency": True,
                    "paperops_watch_only": False,
                    "current_execution_allowed": True,
                    "live_capital_enabled": False,
                    "cadence_seconds": 1200,
                    "current_state": "idle_no_eligible_work",
                }
            ],
        },
    )


def test_operator_service_owns_released_paperops_cadence(tmp_path: Path) -> None:
    _write_ready_runtime(tmp_path)
    status = paperops_runtime_owner_status(_settings(tmp_path))
    projection = operator_service_automation_projection(_settings(tmp_path))

    assert status["active"] is True
    assert status["blockers"] == []
    assert projection is not None
    assert projection["automation_active"] is True
    assert projection["automation_hourly"] is True
    assert projection["automation_prompt_active_trade_bound"] is True


def test_operator_service_fails_closed_when_wrapper_changes(tmp_path: Path) -> None:
    _write_ready_runtime(tmp_path)
    service_path = tmp_path / "qadam_operator_service_status.json"
    payload = json.loads(service_path.read_text(encoding="utf-8"))
    payload["services"][0]["command_sequence"] = [
        [".venv/bin/python", "scripts/direct_broker_submit.py"]
    ]
    _write(service_path, payload)

    status = paperops_runtime_owner_status(_settings(tmp_path))

    assert status["active"] is False
    assert "operator_wrapper_exact" in status["blockers"]
    assert operator_service_automation_projection(_settings(tmp_path)) is None


def test_operator_service_fails_closed_when_live_capital_is_enabled(
    tmp_path: Path,
) -> None:
    _write_ready_runtime(tmp_path)
    settings = replace(_settings(tmp_path), live_capital_enabled=True)

    status = paperops_runtime_owner_status(settings)

    assert status["active"] is False
    assert "live_capital_disabled" in status["blockers"]
