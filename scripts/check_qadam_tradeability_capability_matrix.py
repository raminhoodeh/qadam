#!/usr/bin/env python3
"""Build and validate provider/strategy field collectability."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_tradeability_capabilities import (
    build_and_write_capability_matrix,
)


def main() -> int:
    _payload, checks, errors = build_and_write_capability_matrix()
    print(f"status={checks['status']}")
    print(f"source_count={checks['source_count']}")
    print(f"instrument_count={checks['instrument_count']}")
    print(f"field_count={checks['field_count']}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
