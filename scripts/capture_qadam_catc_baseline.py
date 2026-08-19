#!/usr/bin/env python3
# ruff: noqa: E402
"""Capture CATC-0 state without performing network or broker writes."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_catc_baseline import (
    append_implementation_log,
    capture_catc_baseline,
    write_implementation_status,
)


def main() -> int:
    payload = capture_catc_baseline()
    completed = ["CATC-0"] if payload.get("operator_quiesced") is True else []
    status = write_implementation_status(
        completed_phases=completed,
        in_progress_phase="CATC-1" if completed else "CATC-0",
        blockers=[] if completed else ["operator_service_not_quiesced"],
    )
    append_implementation_log(
        "CATC-0 baseline captured from the dirty worktree and local read-only "
        f"broker mirrors. Operator quiesced: `{payload.get('operator_quiesced')}`. "
        "No order, cancellation, broker write, proof credit, secret edit, or "
        "live-capital change occurred."
    )
    print(json.dumps({"baseline": payload, "implementation_status": status}, indent=2))
    return 0 if completed else 1


if __name__ == "__main__":
    raise SystemExit(main())
