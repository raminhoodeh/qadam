#!/usr/bin/env python3
"""Build and check QEG-4 canonical universe ingestion."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_temporal_graph_ingestion import ingest_canonical_universes


if __name__ == "__main__":
    summary, errors = ingest_canonical_universes()
    print(f"source_identity_count={summary['source_identity_count']}")
    print(f"instrument_identity_count={summary['instrument_identity_count']}")
    print(f"graph_generation_id={summary['graph_generation_id']}")
    print(f"validation_error_count={len(errors)}")
    for error in errors:
        print(f"error={error}")
    raise SystemExit(1 if errors else 0)
