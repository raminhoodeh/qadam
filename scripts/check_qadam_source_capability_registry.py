#!/usr/bin/env python3
# ruff: noqa: E402
"""Build and validate the canonical source capability registry."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_source_capability_registry import (
    build_and_write_source_capability_registry,
)


def main() -> int:
    payload, errors = build_and_write_source_capability_registry()
    from orchestrator.runtime.command import report_work_result
    report_work_result(payload, errors)
    print(f"status={payload['status']}")
    for key, value in payload["counts"].items():
        print(f"{key}={value}")
    for error in errors:
        print(f"error={error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
