#!/usr/bin/env python3
# ruff: noqa: E402
"""Sync lifecycle facts into the canonical append-only control plane."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_lifecycle_control_plane import sync_lifecycle_control_plane


def main() -> int:
    payload = sync_lifecycle_control_plane()
    from orchestrator.runtime.command import report_work_result
    report_work_result(payload, [] if payload["status"] == "passed" else ["lifecycle_sync_failed"])
    print(f"qadam_lifecycle_control_plane_status={payload['status']}")
    print(f"stored_lifecycle_event_count={payload['stored_lifecycle_event_count']}")
    print(f"ambiguous_lifecycle_record_count={payload['ambiguous_lifecycle_record_count']}")
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
