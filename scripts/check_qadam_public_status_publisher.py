#!/usr/bin/env python3
"""Compatibility checker for the one-way public status publisher."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_public_status_bridge_check import (  # noqa: E402
    build_public_status_bridge_check,
)


def main() -> int:
    result = build_public_status_bridge_check()
    print(f"public_status_publisher_check={result['status']}")
    print(f"public_status_publisher_implementation_valid={result['implementation_valid']}")
    print(f"public_status_publisher_operating_ready={result['operating_ready']}")
    print("public_status_publisher_broker_write_count=0")
    return 0 if result["implementation_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
