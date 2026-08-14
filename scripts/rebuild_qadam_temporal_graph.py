#!/usr/bin/env python3
"""Rebuild the disposable QEG SQLite index from canonical events."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_temporal_graph_store import TemporalGraphStore


if __name__ == "__main__":
    manifest = TemporalGraphStore().rebuild()
    print(f"generation_id={manifest['generation_id']}")
    print(f"node_count={manifest['node_count']}")
    print(f"edge_count={manifest['edge_count']}")
