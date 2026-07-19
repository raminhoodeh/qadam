#!/usr/bin/env python3
"""Build and validate the frozen experimental paper policy."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_experimental_paper_policy import (  # noqa: E402
    build_and_write_experimental_policy,
)


def main() -> int:
    policy, mode, _migration, status, errors = build_and_write_experimental_policy()
    print(f"experimental_policy_status={policy['status']}")
    print(f"experimental_policy_version={policy['policy_version']}")
    print(f"experimental_execution_mode={mode['status']}")
    print(
        "experimental_foundation_ready="
        f"{str(status['implementation_foundation_ready']).lower()}"
    )
    for error in errors:
        print(f"experimental_policy_error={error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
