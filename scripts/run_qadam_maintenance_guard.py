#!/usr/bin/env python3
"""Run a maintenance command without overlapping the resident Qadam operator."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_canonical_contracts import AtomicArtifactStore  # noqa: E402
from orchestrator.qadam_operator_ready_common import authority_flags, now_iso  # noqa: E402
from orchestrator.qadam_operator_service import (  # noqa: E402
    MAINTENANCE_ARTIFACT,
    OperatorMaintenanceLock,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-dir", type=Path, required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = list(args.command)
    if command[:1] == ["--"]:
        command = command[1:]
    if not command:
        parser.error("a maintenance command is required after --")

    runtime = args.runtime_dir.expanduser().resolve()
    store = AtomicArtifactStore(runtime)
    lock = OperatorMaintenanceLock(runtime)
    acquired, reason = lock.acquire(blocking=True)
    if not acquired:
        print("qadam_maintenance_guard_status=blocked")
        print(f"qadam_maintenance_guard_reason={reason}")
        return 1

    started_at = now_iso()
    store.write_json(
        MAINTENANCE_ARTIFACT,
        {
            "schema_version": "qadam_operator_maintenance_window.v1",
            "artifact_type": "qadam_operator_maintenance_window",
            "generated_at": started_at,
            "status": "active",
            "owner_pid": os.getpid(),
            "purpose": "deployment_preflight",
            "paper_order_created_count": 0,
            "broker_write_count": 0,
            "authority": authority_flags(),
        },
    )
    try:
        try:
            completed = subprocess.run(command, cwd=ROOT, check=False)
            returncode = int(completed.returncode)
        except KeyboardInterrupt:
            returncode = 130
        except OSError as error:
            print(f"qadam_maintenance_guard_error={error.__class__.__name__}")
            returncode = 127
    finally:
        store.write_json(
            MAINTENANCE_ARTIFACT,
            {
                "schema_version": "qadam_operator_maintenance_window.v1",
                "artifact_type": "qadam_operator_maintenance_window",
                "generated_at": now_iso(),
                "status": "released",
                "started_at": started_at,
                "owner_pid": os.getpid(),
                "purpose": "deployment_preflight",
                "paper_order_created_count": 0,
                "broker_write_count": 0,
                "authority": authority_flags(),
            },
        )
        lock.release()
    print(
        "qadam_maintenance_guard_status="
        + ("passed" if returncode == 0 else "command_failed")
    )
    print(f"qadam_maintenance_guard_returncode={returncode}")
    return returncode


if __name__ == "__main__":
    raise SystemExit(main())
