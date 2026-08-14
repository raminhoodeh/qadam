#!/usr/bin/env python3
"""Build and validate the CTC-0 frozen contract baseline."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_tradeability_baseline import build_and_write_baseline


def main() -> int:
    _payload, checks, errors = build_and_write_baseline()
    print(f"status={checks['status']}")
    print(f"artifact_count={checks['artifact_count']}")
    print(f"parallel_pipeline_detected={str(checks['parallel_pipeline_detected']).lower()}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
