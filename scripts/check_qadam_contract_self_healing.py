#!/usr/bin/env python3
"""Compatibility entrypoint for bounded contract self-healing checks."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_tradeability_reliability import (
    build_and_write_contract_defect_state,
)


def main() -> int:
    summary, checks, errors = build_and_write_contract_defect_state()
    print(f"status={checks.get('status')}")
    print(f"active_defect_count={summary.get('active_defect_count')}")
    for error in errors:
        print(f"error={error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
