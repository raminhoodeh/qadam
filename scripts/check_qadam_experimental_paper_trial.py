#!/usr/bin/env python3
"""Refresh the real-calendar 30-day experimental paper trial projection."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_experimental_paper_trial import (  # noqa: E402
    build_and_write_experimental_paper_trial,
)


def main() -> int:
    summary, _outcomes, checks, errors = build_and_write_experimental_paper_trial()
    print(f"experimental_paper_trial_check_status={checks['status']}")
    print(f"experimental_paper_trial_state={summary['status']}")
    print(f"experimental_paper_trial_day={summary['trial_day']}")
    print(
        "experimental_paper_trial_forward_outcomes="
        f"{summary['experimental_forward_outcome_count']}"
    )
    for error in errors:
        print(f"experimental_paper_trial_validation_error={error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
