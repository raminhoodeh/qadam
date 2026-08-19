#!/usr/bin/env python3
# ruff: noqa: E402
"""Build and validate the typed market-hours execution context."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_execution_context import build_and_write_execution_contexts


def main() -> int:
    contexts, summary, errors = build_and_write_execution_contexts()
    print(f"status={summary['status']}")
    print(f"instrument_count={len(contexts)}")
    print(f"quote_ready_count={summary['quote_ready_count']}")
    for error in errors:
        print(f"error={error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
