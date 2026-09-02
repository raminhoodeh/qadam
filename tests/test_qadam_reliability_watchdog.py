from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import plistlib

from orchestrator.config import Settings
from orchestrator.qadam_operator_ready_common import ROOT
import orchestrator.qadam_reliability_watchdog as watchdog


def _settings(tmp_path: Path) -> Settings:
    return replace(
        Settings.from_env(),
        runtime_dir=str(tmp_path),
        data_root=str(tmp_path.parent),
    )


def _snapshot() -> dict:
    return {
        "operator": {
            "service_running": True,
            "lease_process_alive": True,
            "lease_age_seconds": 10.0,
        }
    }


def _install_contracts(tmp_path: Path, monkeypatch) -> None:
    operator = tmp_path / "operator.plist"
    critic = tmp_path / "critic.plist"
    watchdog_target = tmp_path / "watchdog.plist"
    operator.write_text("operator", encoding="utf-8")
    critic.write_text("critic", encoding="utf-8")
    watchdog_target.write_text("watchdog", encoding="utf-8")
    monkeypatch.setattr(watchdog, "OPERATOR_LAUNCHD_TARGET", operator)
    monkeypatch.setattr(watchdog, "CRITIC_LAUNCHD_TARGET", critic)
    monkeypatch.setattr(watchdog, "LAUNCHD_TARGET", watchdog_target)
    monkeypatch.setattr(watchdog, "installed_template_matches", lambda *_args: True)


def _runner(calls: list[tuple[str, ...]]):
    def execute(command: tuple[str, ...], _timeout: int) -> dict:
        calls.append(command)
        if len(command) > 1 and command[1] == "print":
            running = command[-1].endswith(watchdog.OPERATOR_LAUNCHD_LABEL)
            return {
                "returncode": 0,
                "stdout": "state = running" if running else "state = waiting",
                "stderr": "",
            }
        return {"returncode": 0, "stdout": "", "stderr": ""}

    return execute


def test_healthy_watchdog_observes_without_waking_services(tmp_path, monkeypatch) -> None:
    _install_contracts(tmp_path, monkeypatch)
    monkeypatch.setattr(watchdog, "build_reliability_snapshot", lambda *_a, **_k: _snapshot())
    monkeypatch.setattr(
        watchdog,
        "classify_reliability_snapshot",
        lambda _snapshot: {"healthy": True, "state": "healthy_idle_explained", "blockers": []},
    )
    calls: list[tuple[str, ...]] = []

    payload, errors = watchdog.run_reliability_watchdog(
        _settings(tmp_path),
        command_runner=_runner(calls),
    )

    assert errors == []
    assert payload["status"] == "passed"
    assert payload["operating_state"] == "monitoring"
    assert payload["covered_service_count"] == 21
    assert payload["actions"] == []
    assert not any("kickstart" in command for command in calls)


def test_repairable_runtime_degradation_wakes_critic(tmp_path, monkeypatch) -> None:
    _install_contracts(tmp_path, monkeypatch)
    monkeypatch.setattr(watchdog, "build_reliability_snapshot", lambda *_a, **_k: _snapshot())
    monkeypatch.setattr(
        watchdog,
        "classify_reliability_snapshot",
        lambda _snapshot: {
            "healthy": False,
            "state": "pipeline_degraded_repairable",
            "blockers": [{"code": "operator_service_stale"}],
        },
    )
    calls: list[tuple[str, ...]] = []

    payload, errors = watchdog.run_reliability_watchdog(
        _settings(tmp_path),
        command_runner=_runner(calls),
    )

    assert errors == []
    assert payload["status"] == "recovering"
    assert payload["actions"][0]["action_type"] == "wake_reliability_critic"
    assert any(
        command[:2] == ("launchctl", "kickstart")
        and command[-1].endswith(watchdog.CRITIC_LAUNCHD_LABEL)
        for command in calls
    )


def test_fresh_queued_full_heal_is_not_misclassified_as_stalled(
    tmp_path,
    monkeypatch,
) -> None:
    _install_contracts(tmp_path, monkeypatch)
    monkeypatch.setattr(watchdog, "build_reliability_snapshot", lambda *_a, **_k: _snapshot())
    monkeypatch.setattr(
        watchdog,
        "classify_reliability_snapshot",
        lambda _snapshot: {"healthy": False, "state": "pipeline_degraded_repairable"},
    )
    now = datetime.now(timezone.utc)
    (tmp_path / watchdog.FULL_HEAL_REQUEST_ARTIFACT).write_text(
        json.dumps(
            {
                "request_id": "request-1",
                "status": "requested",
                "generated_at": now.isoformat(),
                "operator_service_contract_hash": watchdog.operator_service_contract_hash(),
            }
        ),
        encoding="utf-8",
    )
    calls: list[tuple[str, ...]] = []

    payload, errors = watchdog.run_reliability_watchdog(
        _settings(tmp_path),
        observed_at=now.isoformat(),
        command_runner=_runner(calls),
    )

    assert errors == []
    assert payload["status"] == "recovering"
    assert payload["operating_state"] == "full_heal_queued"
    assert payload["actions"] == []
    assert not any("kickstart" in command for command in calls)


def test_stalled_full_heal_restarts_singleton_owner(tmp_path, monkeypatch) -> None:
    _install_contracts(tmp_path, monkeypatch)
    monkeypatch.setattr(watchdog, "build_reliability_snapshot", lambda *_a, **_k: _snapshot())
    monkeypatch.setattr(
        watchdog,
        "classify_reliability_snapshot",
        lambda _snapshot: {"healthy": False, "state": "pipeline_degraded_repairable"},
    )
    now = datetime.now(timezone.utc)
    (tmp_path / watchdog.FULL_HEAL_REQUEST_ARTIFACT).write_text(
        json.dumps(
            {
                "request_id": "request-1",
                "status": "requested",
                "generated_at": (now - timedelta(hours=1)).isoformat(),
                "operator_service_contract_hash": watchdog.operator_service_contract_hash(),
            }
        ),
        encoding="utf-8",
    )
    calls: list[tuple[str, ...]] = []

    payload, errors = watchdog.run_reliability_watchdog(
        _settings(tmp_path),
        observed_at=now.isoformat(),
        command_runner=_runner(calls),
    )

    assert errors == []
    assert payload["status"] == "recovering"
    assert payload["operating_state"] == "full_heal_restart_required"
    assert payload["actions"][0]["action_type"] == "restart_operator_owner"
    assert any(command[1:3] == ("kickstart", "-k") for command in calls)


def test_active_resumable_worker_prevents_destructive_stall_restart(
    tmp_path,
    monkeypatch,
) -> None:
    _install_contracts(tmp_path, monkeypatch)
    monkeypatch.setattr(watchdog, "build_reliability_snapshot", lambda *_a, **_k: _snapshot())
    monkeypatch.setattr(
        watchdog,
        "classify_reliability_snapshot",
        lambda _snapshot: {"healthy": False, "state": "pipeline_degraded_repairable"},
    )
    now = datetime.now(timezone.utc)
    (tmp_path / watchdog.FULL_HEAL_REQUEST_ARTIFACT).write_text(
        json.dumps(
            {
                "request_id": "request-1",
                "status": "in_progress",
                "generated_at": (now - timedelta(hours=3)).isoformat(),
                "progress_at": (now - timedelta(hours=3)).isoformat(),
                "current_service_ids": ["power_market_research"],
                "operator_service_contract_hash": watchdog.operator_service_contract_hash(),
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / watchdog.WORKERS_ARTIFACT).write_text(
        json.dumps(
            {
                "workers": {
                    "power_market_research": {
                        "state": "running",
                        "pid": os.getpid(),
                        "started_at": (now - timedelta(minutes=10)).isoformat(),
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    calls: list[tuple[str, ...]] = []

    payload, errors = watchdog.run_reliability_watchdog(
        _settings(tmp_path),
        observed_at=now.isoformat(),
        command_runner=_runner(calls),
    )

    assert errors == []
    assert payload["status"] == "recovering"
    assert payload["operating_state"] == "full_heal_waiting_for_active_worker"
    assert payload["actions"] == []
    assert not any("kickstart" in command for command in calls)


def test_active_full_heal_owner_is_not_restarted_for_stale_normal_lease(
    tmp_path,
    monkeypatch,
) -> None:
    _install_contracts(tmp_path, monkeypatch)
    monkeypatch.setattr(
        watchdog,
        "build_reliability_snapshot",
        lambda *_a, **_k: {
            "operator": {
                "service_running": True,
                "lease_process_alive": True,
                "lease_age_seconds": 20 * 60,
            }
        },
    )
    monkeypatch.setattr(
        watchdog,
        "classify_reliability_snapshot",
        lambda _snapshot: {"healthy": False, "state": "pipeline_degraded_repairable"},
    )
    now = datetime.now(timezone.utc)
    (tmp_path / watchdog.FULL_HEAL_REQUEST_ARTIFACT).write_text(
        json.dumps(
            {
                "request_id": "request-live-owner",
                "status": "in_progress",
                "generated_at": (now - timedelta(minutes=20)).isoformat(),
                "progress_at": (now - timedelta(minutes=2)).isoformat(),
                "owner_pid": os.getpid(),
                "current_service_ids": ["challenger_research"],
                "current_step_timeout_seconds": 7200,
                "operator_service_contract_hash": watchdog.operator_service_contract_hash(),
            }
        ),
        encoding="utf-8",
    )
    calls: list[tuple[str, ...]] = []

    payload, errors = watchdog.run_reliability_watchdog(
        _settings(tmp_path),
        observed_at=now.isoformat(),
        command_runner=_runner(calls),
    )

    assert errors == []
    assert payload["status"] == "recovering"
    assert payload["operating_state"] == "full_heal_in_progress"
    assert payload["actions"] == []
    assert not any("kickstart" in command for command in calls)


def test_watchdog_validator_rejects_any_trading_side_effect() -> None:
    payload = {
        "schema_version": watchdog.SCHEMA_VERSION,
        "artifact_type": "qadam_reliability_watchdog_status",
        "status": "passed",
        "actions": [],
        "paper_order_created_count": 1,
        "broker_write_count": 0,
        "authority": {},
    }

    errors = watchdog.validate_reliability_watchdog_payload(payload)

    assert "watchdog_paper_order_forbidden" in errors


def test_watchdog_launchd_contract_is_fast_and_non_trading() -> None:
    template = (
        ROOT / "ops" / "launchd" / "com.qadam.reliability-watchdog.plist.template"
    ).read_text(encoding="utf-8")
    payload = plistlib.loads(template.replace("__QADAM_ROOT__", str(ROOT)).encode())
    arguments = [str(item) for item in payload["ProgramArguments"]]

    assert payload["Label"] == watchdog.LAUNCHD_LABEL
    assert payload["StartInterval"] == 5 * 60
    assert payload["RunAtLoad"] is True
    assert payload["ProcessType"] == "Standard"
    assert arguments[1].endswith("scripts/run_qadam_reliability_watchdog.py")
    assert all("paperops" not in argument.lower() for argument in arguments)
    assert payload["EnvironmentVariables"]["QADAM_LIVE_CAPITAL_ENABLED"] == "false"
