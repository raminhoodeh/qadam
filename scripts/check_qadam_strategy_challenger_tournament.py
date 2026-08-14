#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_strategy_challenger_tournament import build_strategy_challenger_tournament, validate_strategy_challenger_tournament

if __name__ == "__main__":
    state, build_errors = build_strategy_challenger_tournament()
    errors = sorted(set([*build_errors, *validate_strategy_challenger_tournament()]))
    print(f"status={'passed' if not errors else 'blocked'}")
    print(f"tournament_count={state.get('tournament_count', 0)}")
    print(f"automatic_promotion_count={state.get('automatic_promotion_count', 0)}")
    for error in errors:
        print(f"error={error}")
    raise SystemExit(1 if errors else 0)
