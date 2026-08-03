#!/usr/bin/env python3
"""Fail closed unless Qadam's observable evidence and paper gates align."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_evidence_gate_alignment import (  # noqa: E402
    build_and_write_evidence_gate_alignment,
)


def main() -> int:
    record, errors = build_and_write_evidence_gate_alignment()
    print(f"qadam_evidence_gate_alignment_status={record.get('status')}")
    print(
        "qadam_evidence_gate_backtest_used="
        + str(record.get("backtest_usage", {}).get("used") is True).lower()
    )
    print(
        "qadam_evidence_gate_akber_pass_count="
        + str(record.get("current_alignment", {}).get("akber_pass_count", 0))
    )
    print(f"qadam_evidence_gate_blocker_count={len(errors)}")
    for error in errors:
        print(f"qadam_evidence_gate_blocker={error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
