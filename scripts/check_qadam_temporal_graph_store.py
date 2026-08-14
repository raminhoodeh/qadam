#!/usr/bin/env python3
"""Check QEG-2 append-only graph storage and deterministic rebuild."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_qeg_common import write_phase_status
from orchestrator.qadam_temporal_graph_store import TemporalGraphStore, validate_store


if __name__ == "__main__":
    errors = validate_store()
    manifest = TemporalGraphStore().rebuild()
    write_phase_status(
        "QEG-2", status="passed" if not errors else "blocked",
        implementation_complete=not errors, empirical_state="store_rebuild_verified",
        artifacts=["qadam_temporal_graph_manifest.json", "qadam_temporal_graph_health.json"],
        blockers=errors,
    )
    print(f"generation_id={manifest['generation_id']}")
    print(f"validation_error_count={len(errors)}")
    for error in errors:
        print(f"error={error}")
    raise SystemExit(1 if errors else 0)
