from __future__ import annotations

import json
from pathlib import Path

from orchestrator import qadam_research_supervisor as supervisor


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_released_epoch_supersedes_legacy_supervisor_when_operator_is_running(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(supervisor, "runtime_dir", lambda settings=None: tmp_path)
    monkeypatch.setattr(
        supervisor,
        "_launchd_schedule_state",
        lambda: {
            "launchd_label": supervisor.LAUNCHD_LABEL,
            "target_path": "test",
            "template_installed": True,
            "schedule_loaded": True,
            "worker_process_running_at_probe": False,
            "inspection_only": True,
        },
    )
    _write(
        tmp_path / supervisor.LONG_LOCK_ARTIFACT,
        {"status": "released", "paperops_watch_only_mode": False},
    )
    _write(
        tmp_path / supervisor.OPERATOR_STATUS_ARTIFACT,
        {
            "service_running": True,
            "release_effective": True,
            "liveness": {"process_running": True},
            "services": [
                {"service_id": "forward_shadow", "current_execution_allowed": True}
            ],
        },
    )
    for name in (
        supervisor.ATOMICITY_CHECK_ARTIFACT,
        supervisor.RESUME_CHECK_ARTIFACT,
    ):
        _write(tmp_path / name, {"status": "passed"})

    status, checks, errors = supervisor.build_and_write_research_supervisor()

    assert errors == []
    assert checks["status"] == "passed"
    assert status["status"] == "superseded_by_operator_service"
    assert status["scheduler_owner"] == "qadam_operator_service"
    assert status["paperops_watch_only_mode"] is False
