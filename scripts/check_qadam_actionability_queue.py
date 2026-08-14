#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_actionability_queue import build_actionability_queue


if __name__ == "__main__":
    payload, errors = build_actionability_queue()
    print(f"queue_count={payload['queue_count']}")
    print(f"ready_for_preregistered_experiment_count={payload['ready_for_preregistered_experiment_count']}")
    print(f"validation_error_count={len(errors)}")
    for error in errors:
        print(f"error={error}")
    raise SystemExit(1 if errors else 0)
