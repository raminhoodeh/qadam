#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_graph_active_discovery import build_graph_active_discovery, validate_graph_active_discovery

if __name__ == "__main__":
    state, build_errors = build_graph_active_discovery()
    errors = sorted(set([*build_errors, *validate_graph_active_discovery()]))
    print(f"status={'passed' if not errors else 'blocked'}")
    print(f"evaluated_count={state.get('evaluated_count', 0)}")
    print(f"akber_entered_count={state.get('akber_entered_count', 0)}")
    print(f"paper_review_candidate_count={state.get('paper_review_candidate_count', 0)}")
    for error in errors:
        print(f"error={error}")
    raise SystemExit(1 if errors else 0)
