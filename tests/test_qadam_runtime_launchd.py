from datetime import datetime, timezone
from types import SimpleNamespace
from pathlib import Path
import os
import plistlib
import subprocess
import sys

import pytest

from orchestrator.runtime.launchd import launchd_state
from orchestrator import qadam_reliability_watchdog as watchdog


def test_job_state_survives_long_output_and_ignores_coalitions(monkeypatch):
    output = "gui/501/example = {\n\tstate = running\n\tpid = 123\n"
    output += "\tentry = value\n" * 500
    output += "\tcoalition = {\n\t\tstate = active\n\t}\n}\n"
    monkeypatch.setattr(watchdog.subprocess, "run", lambda *a, **k: SimpleNamespace(
        stdout=output, stderr="", returncode=0,
    ))
    result = watchdog._launchd_state("example", watchdog._default_command_runner)
    assert result["state_known"] is True
    assert result["running"] is True
    assert result["pid"] == 123
    assert "stdout" not in result


def test_nested_running_state_does_not_mark_waiting_job_running():
    result = launchd_state("example", {"returncode": 0, "stdout": (
        "example = {\n state = waiting\n coalition = {\n state = running\n }\n}\n"
    )})
    assert result["running"] is False
    assert result["state"] == "waiting"


def test_missing_or_failed_diagnostic_is_unknown():
    for result in ({"returncode": 124}, {"returncode": 0, "stdout": "truncated"}):
        assert launchd_state("example", result)["state_known"] is False


def test_action_cooldowns_are_independent():
    now = datetime(2026, 9, 6, 16, tzinfo=timezone.utc)
    prior = {"last_action_at_by_type": {"restart_operator_owner": now.isoformat()}}
    assert watchdog._cooldown_active(prior, now, "restart_operator_owner")
    assert not watchdog._cooldown_active(prior, now, "wake_reliability_critic")


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS launch-agent installers use plutil")
@pytest.mark.parametrize("label,installer", [
    ("operator", "operator"),
    ("reliability-critic", "reliability_critic"),
    ("reliability-watchdog", "reliability_watchdog"),
    ("learning-brief", "learning_brief"),
    ("telegram-readonly-interface", "telegram_readonly_interface"),
])
def test_active_launch_agents_install_logs_outside_desktop(tmp_path, label, installer):
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        ["sh", str(root / "scripts" / f"install_qadam_{installer}_launch_agent.sh")],
        env={**os.environ, "HOME": str(tmp_path)}, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    target = tmp_path / "Library" / "LaunchAgents" / f"com.qadam.{label}.plist"
    payload = plistlib.loads(target.read_bytes())
    assert payload["WorkingDirectory"] == str(root)
    for key in ("StandardOutPath", "StandardErrorPath"):
        assert Path(payload[key]).parent == tmp_path / "Library" / "Logs" / "Qadam"
    assert "__QADAM_" not in target.read_text()
    assert (tmp_path / "Library" / "Logs" / "Qadam").is_dir()
