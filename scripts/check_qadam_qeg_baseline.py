#!/usr/bin/env python3
"""Build and check QEG-0 baseline."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_qeg_baseline import build_and_write_baseline


if __name__ == "__main__":
    baseline, errors = build_and_write_baseline()
    print(f"status={baseline['status']}")
    print(f"source_count={baseline['source_count']}")
    print(f"instrument_count={baseline['instrument_count']}")
    print(f"validation_error_count={len(errors)}")
    for error in errors:
        print(f"error={error}")
    raise SystemExit(1 if errors else 0)
