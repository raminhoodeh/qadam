#!/usr/bin/env python3
"""Build and validate the sole canonical tradeability compilation lane."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_tradeability_pipeline import (
    build_and_write_tradeability_pipeline,
)
from orchestrator.qadam_tradeability_reliability import (
    build_and_write_contract_defect_state,
)


def main() -> int:
    _state, checks, errors = build_and_write_tradeability_pipeline()
    _defect_summary, _defect_checks, defect_errors = (
        build_and_write_contract_defect_state()
    )
    for key in (
        "status",
        "implementation_complete",
        "source_draft_count",
        "envelope_count",
        "projection_count",
        "rejection_count",
        "contract_defect_count",
        "candidate_created_count",
        "order_created_count",
        "broker_write_count",
    ):
        print(f"{key}={checks.get(key)}")
    for error in [*errors, *defect_errors]:
        print(f"error={error}")
    return 0 if not errors and not defect_errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
