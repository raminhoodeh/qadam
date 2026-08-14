#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_strategy_foundry_v4 import build_strategy_foundry_v4, validate_strategy_foundry_v4

if __name__ == "__main__":
    state, build_errors = build_strategy_foundry_v4()
    errors = sorted(set([*build_errors, *validate_strategy_foundry_v4()]))
    print(f"status={'passed' if not errors else 'blocked'}")
    print(f"strategy_version_count={state.get('strategy_version_count', 0)}")
    print(f"rejection_count={state.get('rejection_count', 0)}")
    for error in errors:
        print(f"error={error}")
    raise SystemExit(1 if errors else 0)
