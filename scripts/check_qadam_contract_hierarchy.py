#!/usr/bin/env python3
"""Validate Qadam instruction precedence and immutable authority boundaries."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_tradeability_baseline import build_and_write_baseline


def main() -> int:
    payload, _checks, _errors = build_and_write_baseline()
    errors = list(payload["precedence"].get("validation_errors") or [])
    print(f"status={'passed' if not errors else 'blocked'}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
