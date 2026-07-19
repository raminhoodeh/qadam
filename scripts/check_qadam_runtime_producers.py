#!/usr/bin/env python3
"""Validate canonical runtime producers and optionally refresh safe owners."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_runtime_producers import (  # noqa: E402
    build_registry,
    refresh_safe_producers,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-safe", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    closure = refresh_safe_producers() if args.refresh_safe else None
    registry = build_registry()
    print(f"runtime_producer_registry_status={registry.get('status')}")
    print(f"runtime_producer_count={registry.get('producer_count')}")
    print(f"runtime_producer_artifact_count={registry.get('artifact_count')}")
    print(
        "runtime_producer_stale_or_missing_count="
        f"{registry.get('stale_or_missing_artifact_count')}"
    )
    print(f"runtime_producer_duplicate_owner_count={registry.get('duplicate_owner_count')}")
    if closure is not None:
        print(f"runtime_refresh_status={closure.get('status')}")
        print(f"runtime_refresh_failed_producer_count={closure.get('failed_producer_count')}")
    passed = (
        registry.get("status") == "passed"
        and registry.get("duplicate_owner_count") == 0
        and (closure is None or closure.get("failed_producer_count") == 0)
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
