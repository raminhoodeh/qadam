#!/usr/bin/env python3
"""Bootstrap registered Qadam runtime artifacts into immutable generations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_artifact_generations import (  # noqa: E402
    GenerationError,
    bootstrap_registered_generations,
)
from orchestrator.qadam_operator_ready_common import (  # noqa: E402
    authority_flags,
    now_iso,
    runtime_dir,
    write_json_atomic,
)

REGISTRY_PATH = ROOT / "config" / "qadam_runtime_artifact_ownership.json"
ARTIFACT_NAME = "qadam_artifact_generation_migration.json"


def _records() -> list[dict[str, object]]:
    payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    records = payload.get("artifacts") if isinstance(payload, dict) else None
    if not isinstance(records, list):
        raise ValueError("artifact_ownership_registry_invalid")
    return records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Publish generation-zero snapshots. Without this flag, run preflight only.",
    )
    arguments = parser.parse_args()
    runtime = runtime_dir()
    records = _records()
    missing = sorted(
        str(record.get("artifact") or "")
        for record in records
        if not (runtime / str(record.get("artifact") or "")).is_file()
    )
    if missing:
        result = {
            "schema_version": "qadam_artifact_generation_migration.v1",
            "artifact_type": "qadam_artifact_generation_migration",
            "generated_at": now_iso(),
            "status": "blocked",
            "mode": "preflight",
            "blockers": ["registered_runtime_artifact_missing"],
            "missing_artifacts": missing,
            "paper_order_created_count": 0,
            "broker_write_count": 0,
            "authority": authority_flags(),
        }
        write_json_atomic(runtime / ARTIFACT_NAME, result)
        print("qadam_generation_migration_status=blocked")
        print(f"qadam_generation_migration_missing_count={len(missing)}")
        return 1
    if not arguments.execute:
        print("qadam_generation_migration_status=ready")
        print(f"qadam_generation_migration_artifact_count={len(records)}")
        print("qadam_generation_migration_execute=false")
        return 0
    try:
        result = bootstrap_registered_generations(runtime, records)
    except (GenerationError, OSError, ValueError) as error:
        result = {
            "schema_version": "qadam_artifact_generation_migration.v1",
            "artifact_type": "qadam_artifact_generation_migration",
            "generated_at": now_iso(),
            "status": "blocked",
            "mode": "execute",
            "blockers": [f"{type(error).__name__}:{error}"],
            "paper_order_created_count": 0,
            "broker_write_count": 0,
            "authority": authority_flags(),
        }
        write_json_atomic(runtime / ARTIFACT_NAME, result)
        print("qadam_generation_migration_status=blocked")
        print(f"qadam_generation_migration_error={type(error).__name__}:{error}")
        return 1
    write_json_atomic(runtime / ARTIFACT_NAME, result)
    print("qadam_generation_migration_status=passed")
    print(f"qadam_generation_migration_resource_count={result['resource_count']}")
    print(f"qadam_generation_migration_artifact_count={result['artifact_count']}")
    print("qadam_generation_migration_broker_write_count=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
