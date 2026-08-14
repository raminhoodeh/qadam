#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_graph_outcome_learning import build_graph_outcome_learning, validate_graph_outcome_learning

if __name__ == "__main__":
    state, build_errors = build_graph_outcome_learning()
    errors = sorted(set([*build_errors, *validate_graph_outcome_learning()]))
    print(f"status={'passed' if not errors else 'blocked'}")
    print(f"learning_record_count={state.get('learning_record_count', 0)}")
    print(f"proposal_count={state.get('proposal_count', 0)}")
    for error in errors:
        print(f"error={error}")
    raise SystemExit(1 if errors else 0)
