#!/usr/bin/env python3
"""Build and validate EF-6 risk and Router alignment artifacts."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_risk_router_alignment import (  # noqa: E402
    build_and_write_risk_router_alignment,
)


def main() -> int:
    _, checks, errors = build_and_write_risk_router_alignment()
    from orchestrator.runtime.command import report_work_result
    report_work_result(checks, errors)
    print(f"qadam_risk_router_alignment_status={checks['status']}")
    print(
        "qadam_risk_router_alignment_concentration_rows="
        f"{checks['channel_concentration_record_count']}"
    )
    print(
        "qadam_risk_router_alignment_router_decisions="
        f"{checks['router_decision_count']}"
    )
    for error in errors:
        print(f"qadam_risk_router_alignment_error={error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
