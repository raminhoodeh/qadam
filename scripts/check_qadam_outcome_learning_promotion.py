#!/usr/bin/env python3
"""Build and validate EF-8 outcome learning and strategy promotion."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_outcome_learning_promotion import (  # noqa: E402
    build_and_write_outcome_learning_promotion,
)


def main() -> int:
    _, checks, errors = build_and_write_outcome_learning_promotion()
    print(f"qadam_outcome_learning_promotion_status={checks['status']}")
    print(f"qadam_outcome_learning_outcomes={checks['outcome_record_count']}")
    print(
        "qadam_outcome_learning_mature_real_outcomes="
        f"{checks['mature_real_outcome_count']}"
    )
    print(
        "qadam_outcome_learning_auto_admissions="
        f"{checks['automatic_emerging_paper_admission_count']}"
    )
    for error in errors:
        print(f"qadam_outcome_learning_promotion_error={error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
