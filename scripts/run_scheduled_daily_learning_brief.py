#!/usr/bin/env python3
"""Run a due, unsent learning-brief slot with a lightweight retry guard."""

from __future__ import annotations

import fcntl
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.daily_learning_scheduler import (  # noqa: E402
    build_daily_learning_scheduler_decision,
    write_daily_learning_scheduler_attempt,
)
from orchestrator.qadam_operator_ready_common import runtime_dir  # noqa: E402
from orchestrator.qadam_resource_locks import (  # noqa: E402
    ResourceClaims,
    ResourceLease,
)


def _read_automation(settings: Settings) -> dict:
    path = Path(settings.runtime_dir) / "daily_learning_automation.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def main() -> int:
    settings = Settings.from_env()
    lock_path = Path(settings.runtime_dir) / ".daily_learning_scheduler.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0
        decision = build_daily_learning_scheduler_decision(settings=settings)
        if decision["should_run"] is not True:
            return 0
        with ResourceLease(
            runtime_dir(settings),
            service_id="daily_learning_scheduler",
            claims=ResourceClaims(
                reads=(
                    "source_lake",
                    "price_lake",
                    "point_in_time_evidence",
                    "score_plane",
                    "label_plane",
                    "edge_registry",
                    "paper_state",
                ),
                writes=("learning_plane", "dashboard_projection"),
            ),
            timeout_seconds=120,
        ):
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/run_daily_learning_automation.py"),
                    "--live",
                ],
                cwd=ROOT,
                check=False,
            )
        automation = _read_automation(settings)
        write_daily_learning_scheduler_attempt(
            decision=decision,
            exit_code=result.returncode,
            automation=automation,
            settings=settings,
        )
        return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
