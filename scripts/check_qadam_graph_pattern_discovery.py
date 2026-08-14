#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_graph_pattern_discovery import build_graph_patterns


if __name__ == "__main__":
    payload, errors = build_graph_patterns()
    print(f"candidate_count={payload['candidate_count']}")
    print(f"active_trigger_candidate_count={payload['active_trigger_candidate_count']}")
    print(f"validation_error_count={len(errors)}")
    for error in errors:
        print(f"error={error}")
    raise SystemExit(1 if errors else 0)
