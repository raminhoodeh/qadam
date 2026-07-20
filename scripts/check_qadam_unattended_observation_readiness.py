#!/usr/bin/env python3
"""Certify Qadam is safe to leave running in the current paper epoch."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_unattended_observation_readiness import (  # noqa: E402
    build_and_write_unattended_observation_readiness,
)


def main() -> int:
    payload, checks, errors = build_and_write_unattended_observation_readiness(
        Settings.from_env()
    )
    print(f"qadam_observation_readiness_status={checks['status']}")
    print(
        "safe_to_leave_running_and_observe="
        f"{str(payload['safe_to_leave_running_and_observe']).lower()}"
    )
    print(f"engineering_blocker_count={payload['engineering_blocker_count']}")
    for blocker in payload["engineering_blockers"]:
        print(f"engineering_blocker={blocker}")
    for item in payload["real_time_maturity"]:
        print(
            f"real_time_maturity={item['requirement']}:{item['state']}:{item['progress']}"
        )
    for error in errors:
        print(f"validation_error={error}")
    return 0 if checks["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
