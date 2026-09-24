#!/usr/bin/env python3
"""Refresh Qadam-owned strategy decisions; never submit broker orders."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from orchestrator.qadam_strategy_decision import build_and_write_strategy_decision


def main():
    _, checks, errors = build_and_write_strategy_decision()
    from orchestrator.runtime.command import report_work_result
    report_work_result(checks, errors)
    print(checks)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
