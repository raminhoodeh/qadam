#!/usr/bin/env python3
"""Run bounded local storage maintenance without touching trading authority."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_operator_ready_common import runtime_dir  # noqa: E402
from orchestrator.qadam_storage_retention import run_storage_maintenance  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    status = run_storage_maintenance(
        runtime_dir(Settings.from_env()),
        force=args.force,
        apply=not args.preview,
    )
    print(f"status={status.get('status')}")
    print(f"maintenance_applied={status.get('maintenance_applied')}")
    print(f"disk_free_bytes={status.get('disk', {}).get('free_bytes')}")
    print(
        "write_services_allowed="
        + str(status.get("disk", {}).get("write_services_allowed") is True).lower()
    )
    return 0 if status.get("disk", {}).get("write_services_allowed") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
