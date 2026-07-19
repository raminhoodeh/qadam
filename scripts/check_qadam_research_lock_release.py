#!/usr/bin/env python3
"""Audit research-lock release readiness without modifying the lock."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_operator_ready_common import runtime_dir  # noqa: E402
from orchestrator.qadam_router_v3_paperops import (  # noqa: E402
    RELEASE_CHECK_ARTIFACT,
    RELEASE_READINESS_ARTIFACT,
    build_and_write_release_readiness,
)


def main() -> int:
    settings = Settings.from_env()
    runtime = runtime_dir(settings)
    _release, checks, errors = build_and_write_release_readiness(settings)
    print(f"artifact={runtime / RELEASE_READINESS_ARTIFACT}")
    print(f"checks_artifact={runtime / RELEASE_CHECK_ARTIFACT}")
    for key in (
        "status",
        "implementation_ready",
        "release_state",
        "release_recommended",
        "release_performed",
        "nonpassing_phase_count",
        "blocker_count",
        "broker_write_count",
    ):
        print(f"{key}={checks[key]}")
    print(f"validation_error_count={len(errors)}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
