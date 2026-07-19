#!/usr/bin/env python3
"""Build the final three-state experimental paper-epoch certification."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_autonomous_experimental_paper_epoch import (  # noqa: E402
    build_and_write_autonomous_experimental_paper_epoch_certification,
)


def main() -> int:
    certification, checks, errors = (
        build_and_write_autonomous_experimental_paper_epoch_certification()
    )
    print(f"experimental_epoch_certification_check={checks['status']}")
    print(
        "experimental_epoch_implementation_complete="
        f"{str(certification['implementation_complete']).lower()}"
    )
    print(
        "experimental_epoch_operation_running="
        f"{str(certification['autonomous_experimental_paper_operation_running']).lower()}"
    )
    print(
        "experimental_epoch_unattended_reliability_certified="
        f"{str(certification['unattended_reliability_certified']).lower()}"
    )
    print(f"experimental_epoch_trial_day={certification['trial']['day']}")
    print(f"experimental_epoch_validated_edge_count={certification['validated_edge_count']}")
    for blocker in certification["operation_blockers"]:
        print(f"experimental_epoch_operation_blocker={blocker}")
    for blocker in certification["unattended_reliability_blockers"]:
        print(f"experimental_epoch_reliability_blocker={blocker}")
    for error in errors:
        print(f"experimental_epoch_validation_error={error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
