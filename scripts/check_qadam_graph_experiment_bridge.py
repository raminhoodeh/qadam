#!/usr/bin/env python3
"""Build and validate QEG-8."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_graph_experiment_bridge import build_graph_experiment_bridge, validate_graph_experiment_bridge


if __name__ == "__main__":
    state, build_errors = build_graph_experiment_bridge()
    errors = sorted(set([*build_errors, *validate_graph_experiment_bridge()]))
    print(f"status={'passed' if not errors else 'blocked'}")
    print(f"preregistered_experiment_count={state.get('preregistered_experiment_count', 0)}")
    print(f"backtest_registry_experiment_count={state.get('backtest_registry_experiment_count', 0)}")
    for error in errors:
        print(f"error={error}")
    raise SystemExit(1 if errors else 0)
