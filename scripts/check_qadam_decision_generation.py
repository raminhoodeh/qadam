#!/usr/bin/env python3
"""Verify current decision artifacts share one complete generation."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_tradeability_audits import (
    build_and_write_decision_generation_audit,
)


def main() -> int:
    manifest, checks, errors = build_and_write_decision_generation_audit()
    print(f"status={checks.get('status')}")
    print(f"generation_state={manifest.get('status')}")
    print(f"current_hypothesis_count={manifest.get('current_hypothesis_count')}")
    print(f"mixed_generation_join_count={manifest.get('mixed_generation_join_count')}")
    print(
        "partial_generation_current_count="
        f"{manifest.get('partial_generation_current_count')}"
    )
    for error in errors:
        print(f"error={error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
