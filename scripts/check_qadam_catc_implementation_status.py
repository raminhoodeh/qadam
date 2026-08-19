#!/usr/bin/env python3
# ruff: noqa: E402
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_catc_implementation_status import (
    build_and_write_catc_implementation_status,
)


def main() -> int:
    payload = build_and_write_catc_implementation_status()
    print(f"qadam_catc_implementation_status={payload['status']}")
    print(f"implemented_phase_count={payload['implemented_phase_count']}")
    print(f"phase_count={payload['phase_count']}")
    return 0 if not payload["blockers"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
