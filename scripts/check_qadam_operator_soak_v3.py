#!/usr/bin/env python3
"""Refresh version-bound post-release unattended reliability evidence."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_operator_soak_v3 import (  # noqa: E402
    build_and_write_operator_soak_v3,
)


def main() -> int:
    soak, _probes, checks, errors = build_and_write_operator_soak_v3()
    print(f"operator_soak_v3_check_status={checks['status']}")
    print(f"operator_soak_v3_state={soak['status']}")
    print(
        "operator_soak_v3_real_sessions="
        f"{soak['completed_real_session_count']}/{soak['required_real_session_count']}"
    )
    print(
        "operator_soak_v3_unattended_reliability_certified="
        f"{str(soak['unattended_reliability_certified']).lower()}"
    )
    for blocker in soak["blockers"]:
        print(f"operator_soak_v3_blocker={blocker}")
    for error in errors:
        print(f"operator_soak_v3_validation_error={error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
