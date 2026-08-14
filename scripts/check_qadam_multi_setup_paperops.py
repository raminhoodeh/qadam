#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_multi_setup_paperops import build_multi_setup_paperops, validate_multi_setup_paperops

if __name__ == "__main__":
    state, build_errors = build_multi_setup_paperops()
    errors = sorted(set([*build_errors, *validate_multi_setup_paperops()]))
    print(f"status={'passed' if not errors else 'blocked'}")
    print(f"decision_count={state.get('decision_count', 0)}")
    print(f"handoff_count={state.get('handoff_count', 0)}")
    for error in errors:
        print(f"error={error}")
    raise SystemExit(1 if errors else 0)
