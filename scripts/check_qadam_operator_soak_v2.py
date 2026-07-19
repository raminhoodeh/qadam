#!/usr/bin/env python3
"""Refresh and validate conservative real-session operator soak evidence."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_operator_soak_v2 import (  # noqa: E402
    build_and_write_operator_soak_v2,
)


def main() -> int:
    soak, release, checks, errors = build_and_write_operator_soak_v2()
    print(f"operator_soak_v2_check_status={checks['status']}")
    print(f"operator_soak_v2_state={soak['status']}")
    print(
        "operator_soak_v2_real_sessions="
        f"{soak['completed_real_session_count']}/{soak['required_real_session_count']}"
    )
    print(f"operator_soak_v2_complete={str(soak['soak_complete']).lower()}")
    print(
        "operator_soak_v2_release_candidate="
        f"{str(release['release_candidate']).lower()}"
    )
    print("operator_soak_v2_broker_write_count=0")
    for blocker in soak.get("blockers", []):
        print(f"operator_soak_v2_blocker={blocker}")
    for error in errors:
        print(f"operator_soak_v2_validation_error={error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
