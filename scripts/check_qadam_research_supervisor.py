#!/usr/bin/env python3
"""Build and validate the OR-1 research supervisor contract."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_research_supervisor import (  # noqa: E402
    CHECK_ARTIFACT,
    HEARTBEAT_ARTIFACT,
    MANIFEST_ARTIFACT,
    RESUME_ARTIFACT,
    STATUS_ARTIFACT,
    build_and_write_research_supervisor,
)
from orchestrator.qadam_operator_ready_common import runtime_dir  # noqa: E402


def main() -> int:
    settings = Settings.from_env()
    runtime = runtime_dir(settings)
    status, checks, errors = build_and_write_research_supervisor(settings)
    for name in (STATUS_ARTIFACT, HEARTBEAT_ARTIFACT, MANIFEST_ARTIFACT, RESUME_ARTIFACT, CHECK_ARTIFACT):
        print(f"artifact={runtime / name}")
    print(f"status={checks['status']}")
    print(f"supervisor_runtime_state={status['status']}")
    print(f"supervisor_installed={status['supervisor_installed']}")
    print(f"manifest_job_count={checks['manifest_job_count']}")
    print(f"paperops_watch_only_mode={checks['paperops_watch_only_mode']}")
    print(f"validation_error_count={len(errors)}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
