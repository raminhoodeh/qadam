#!/usr/bin/env python3
"""Validate Qadam's live disk guard and bounded retention state."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_operator_ready_common import runtime_dir  # noqa: E402
from orchestrator.qadam_storage_retention import (  # noqa: E402
    run_storage_maintenance,
    validate_storage_status,
)


def main() -> int:
    status = run_storage_maintenance(
        runtime_dir(Settings.from_env()),
        force=False,
        apply=True,
    )
    errors = validate_storage_status(status)
    print("qadam_storage_retention_status=" + ("passed" if not errors else "blocked"))
    print(f"qadam_storage_disk_free_bytes={status.get('disk', {}).get('free_bytes')}")
    print(
        "qadam_storage_live_disk_measurement="
        + str(
            status.get("disk", {}).get("measurement_source")
            == "shutil.disk_usage_live_filesystem"
        ).lower()
    )
    print(
        "qadam_storage_write_services_allowed="
        + str(status.get("disk", {}).get("write_services_allowed") is True).lower()
    )
    print(f"qadam_storage_validation_error_count={len(errors)}")
    for error in errors:
        print(f"qadam_storage_error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
