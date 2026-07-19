#!/usr/bin/env python3
"""Build and validate bounded experimental paper eligibility."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_experimental_paper_eligibility import (
    build_and_write_experimental_eligibility,
)


def main() -> int:
    state, checks, errors = build_and_write_experimental_eligibility()
    print(f"qadam_experimental_paper_eligibility_status={checks['status']}")
    print(
        "qadam_experimental_paper_candidate_count="
        f"{checks['experimental_candidate_count']}"
    )
    print(
        "qadam_experimental_paper_operating_state="
        f"{state['status']['status']}"
    )
    for error in errors:
        print(f"qadam_experimental_paper_eligibility_error={error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
