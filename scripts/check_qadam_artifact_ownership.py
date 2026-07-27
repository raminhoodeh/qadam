#!/usr/bin/env python3
"""Validate hot-artifact ownership and service dependencies."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_artifact_ownership import (  # noqa: E402
    build_artifact_ownership_audit,
)


def main() -> int:
    result = build_artifact_ownership_audit()
    print(f"qadam_artifact_ownership_status={result['status']}")
    print(f"qadam_artifact_owner_count={result['registered_artifact_count']}")
    print(f"qadam_artifact_multi_writer_count={result['multi_writer_violation_count']}")
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
