#!/usr/bin/env python3
"""Validate the narrow experimental PaperOps release without executing it."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_guarded_paper_launch import (  # noqa: E402
    build_current_experimental_release_state,
    build_experimental_guarded_launch_checks,
)
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore  # noqa: E402
from orchestrator.qadam_operator_ready_common import runtime_dir  # noqa: E402


def main() -> int:
    readiness = build_current_experimental_release_state()
    AtomicArtifactStore(runtime_dir()).write_json(
        "qadam_experimental_paper_release_readiness.json", readiness
    )
    checks, errors = build_experimental_guarded_launch_checks()
    print(f"qadam_experimental_release_check_status={checks['status']}")
    print(
        "qadam_experimental_release_readiness="
        f"{readiness['status']}"
    )
    print(
        "qadam_autonomous_experimental_paper_operation_running="
        f"{checks['autonomous_experimental_paper_operation_running']}"
    )
    for blocker in readiness.get("blockers", []):
        print(f"qadam_experimental_release_blocker={blocker}")
    for error in errors:
        print(f"qadam_experimental_release_error={error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
