#!/usr/bin/env python3
"""Validate current-paper-epoch isolation across dashboard artifacts."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_dashboard_epoch_isolation import (  # noqa: E402
    build_dashboard_epoch_isolation,
    validate_dashboard_epoch_isolation,
)


def main() -> int:
    payload = build_dashboard_epoch_isolation()
    errors = validate_dashboard_epoch_isolation(payload)
    print(f"dashboard_epoch_isolation_status={payload['status']}")
    print(f"dashboard_epoch_clean_active={str(payload['clean_epoch_active']).lower()}")
    print(f"dashboard_epoch_current_rows={payload['current_execution_row_count']}")
    print(f"dashboard_epoch_mismatched_rows={payload['epoch_mismatched_row_count']}")
    print(f"dashboard_epoch_archived_id_leaks={payload['archived_identifier_leak_count']}")
    print("dashboard_epoch_broker_write_count=0")
    for error in errors:
        print(f"dashboard_epoch_error={error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
