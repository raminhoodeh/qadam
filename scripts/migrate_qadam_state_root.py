#!/usr/bin/env python3
"""Prepare a reviewed Qadam state-root migration without changing configuration."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_operator_ready_common import (  # noqa: E402
    authority_flags,
    now_iso,
    runtime_dir,
    write_json_atomic,
)
from orchestrator.qadam_state_root import tree_digest  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    settings = Settings.from_env()
    source_runtime = runtime_dir(settings).resolve()
    data_root = Path(settings.data_root)
    if not data_root.is_absolute():
        data_root = ROOT / data_root
    source_research = (data_root / "research").resolve()
    target = Path(args.target).expanduser().resolve()
    required_bytes = (
        tree_digest(source_runtime)["byte_count"] + tree_digest(source_research)["byte_count"]
    )
    free_bytes = shutil.disk_usage(target.parent if target.parent.exists() else ROOT).free
    blockers = []
    if target in {source_runtime, source_research}:
        blockers.append("migration_target_matches_source")
    if free_bytes < required_bytes + 10 * 1024**3:
        blockers.append("insufficient_disk_for_checksum_complete_copy")
    executed = False
    if args.execute and not blockers:
        shutil.copytree(source_runtime, target / "runtime", dirs_exist_ok=True)
        shutil.copytree(source_research, target / "research", dirs_exist_ok=True)
        executed = True
    result = {
        "schema_version": "qadam_state_root_migration.v1",
        "artifact_type": "qadam_state_root_migration",
        "generated_at": now_iso(),
        "status": "copied_pending_activation" if executed else "planned",
        "source_runtime": tree_digest(source_runtime),
        "source_research": tree_digest(source_research),
        "target": str(target),
        "required_bytes": required_bytes,
        "free_bytes": free_bytes,
        "blockers": blockers,
        "configuration_changed": False,
        "activation_instruction": (
            "Set QADAM_STATE_ROOT, QADAM_RUNTIME_DIR and QADAM_DATA_ROOT only "
            "after reviewing copied checksums; this script never edits secrets or .env files."
        ),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "authority": authority_flags(),
    }
    output = source_runtime / "qadam_state_root_migration.json"
    write_json_atomic(output, result)
    print(f"qadam_state_root_migration_status={result['status']}")
    print(f"qadam_state_root_migration_blocker_count={len(blockers)}")
    return 0 if not (args.execute and blockers) else 1


if __name__ == "__main__":
    raise SystemExit(main())
