#!/usr/bin/env python3
# ruff: noqa: E402
"""Validate CATC storage, lifecycle import, and rebuildable projections."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_control_plane_migration import import_legacy_control_plane
from orchestrator.qadam_lifecycle_control_plane import sync_lifecycle_control_plane
from orchestrator.qadam_projection_outbox import rebuild_control_plane_projections


def main() -> int:
    migration = import_legacy_control_plane()
    lifecycle = sync_lifecycle_control_plane()
    projections = rebuild_control_plane_projections()
    statuses = [migration.get("status"), lifecycle.get("status"), projections.get("status")]
    status = "passed" if all(value == "passed" for value in statuses) else "blocked"
    print(f"qadam_control_plane_status={status}")
    print(f"lifecycle_event_count={lifecycle.get('stored_lifecycle_event_count', 0)}")
    print(f"missing_handoff_lineage_count={lifecycle.get('missing_handoff_lineage_count', 0)}")
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
