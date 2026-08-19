#!/usr/bin/env python3
# ruff: noqa: E402
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_catc_dashboard_projection import build_and_write_catc_dashboard_projection


def main() -> int:
    payload, errors = build_and_write_catc_dashboard_projection()
    print(f"qadam_catc_dashboard_projection_status={payload['status']}")
    print(f"validation_error_count={len(errors)}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
