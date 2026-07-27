#!/usr/bin/env python3
"""Capture a checksum-complete operator incident baseline without mutation."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_operator_ready_common import (  # noqa: E402
    authority_flags,
    file_sha256,
    now_iso,
    read_json,
    runtime_dir,
    write_json_atomic,
)
from orchestrator.qadam_operator_service import (  # noqa: E402
    CIRCUIT_BREAKERS_ARTIFACT,
    LEASE_ARTIFACT,
    RECEIPTS_ARTIFACT,
    RECEIPT_INDEX_ARTIFACT,
    REPAIR_QUEUE_ARTIFACT,
    STATUS_ARTIFACT,
    WORKERS_ARTIFACT,
    operator_build_identity,
)
from orchestrator.qadam_state_root import build_state_root_preflight  # noqa: E402

CAPTURE_ARTIFACTS = (
    CIRCUIT_BREAKERS_ARTIFACT,
    REPAIR_QUEUE_ARTIFACT,
    RECEIPT_INDEX_ARTIFACT,
    RECEIPTS_ARTIFACT,
    WORKERS_ARTIFACT,
    LEASE_ARTIFACT,
    "qadam_operator_dashboard_freshness.json",
    "paperops_autonomous_pass_summary.json",
    STATUS_ARTIFACT,
)


def _process_inventory() -> list[dict[str, object]]:
    result = subprocess.run(
        ["ps", "-axo", "pid=,ppid=,etime=,command="],
        capture_output=True,
        text=True,
        check=False,
    )
    records = []
    for line in result.stdout.splitlines():
        if "qadam" not in line.lower() and "run_paperops" not in line.lower():
            continue
        parts = line.strip().split(None, 3)
        if len(parts) != 4:
            continue
        records.append(
            {
                "pid": int(parts[0]),
                "parent_pid": int(parts[1]),
                "elapsed": parts[2],
                "command": parts[3],
            }
        )
    return records


def main() -> int:
    runtime = runtime_dir()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive = runtime / "archive" / f"porr-{stamp}"
    archive.mkdir(parents=True, exist_ok=False)
    copied = []
    for name in CAPTURE_ARTIFACTS:
        source = runtime / name
        if not source.is_file():
            continue
        destination = archive / name
        shutil.copy2(source, destination)
        copied.append(
            {
                "artifact": name,
                "size_bytes": destination.stat().st_size,
                "sha256": file_sha256(destination),
            }
        )
    processes = _process_inventory()
    process_payload = {
        "schema_version": "qadam_porr_process_inventory.v1",
        "artifact_type": "qadam_porr_process_inventory",
        "generated_at": now_iso(),
        "processes": processes,
        "active_writer_candidates": [
            row
            for row in processes
            if any(
                token in str(row.get("command") or "")
                for token in (
                    "run_qadam_operator_service.py",
                    "run_qadam_operator_worker.py",
                    "run_scheduled_daily_learning_brief.py",
                )
            )
        ],
        "authority": authority_flags(),
    }
    write_json_atomic(runtime / "qadam_porr_process_inventory.json", process_payload)
    filesystem = build_state_root_preflight()
    write_json_atomic(runtime / "qadam_porr_filesystem_preflight.json", filesystem)
    baseline = {
        "schema_version": "qadam_porr_incident_baseline.v1",
        "artifact_type": "qadam_porr_incident_baseline",
        "generated_at": now_iso(),
        "status": "captured",
        "archive_path": str(archive),
        "build_identity": operator_build_identity(),
        "python_environment": {
            "executable": sys.executable,
            "version": sys.version,
        },
        "copied_artifacts": copied,
        "copied_artifact_count": len(copied),
        "archive_manifest_sha256": hashlib.sha256(
            "\n".join(f"{row['artifact']}:{row['sha256']}" for row in copied).encode("utf-8")
        ).hexdigest(),
        "circuit_state": read_json(runtime / CIRCUIT_BREAKERS_ARTIFACT),
        "operator_was_quiesced": not process_payload["active_writer_candidates"],
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "authority": authority_flags(),
    }
    write_json_atomic(runtime / "qadam_porr_incident_baseline.json", baseline)
    write_json_atomic(archive / "manifest.json", baseline)
    print("qadam_porr_incident_status=captured")
    print(f"qadam_porr_incident_archive={archive}")
    print(f"qadam_porr_operator_quiesced={baseline['operator_was_quiesced']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
