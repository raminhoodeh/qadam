#!/usr/bin/env python3
"""Validate Qadam's canonical local state root."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_state_root import build_state_root_preflight  # noqa: E402


def main() -> int:
    result = build_state_root_preflight()
    print(f"qadam_state_root_status={result['status']}")
    print(f"qadam_state_root={result['state_root']}")
    print(f"qadam_state_root_blocker_count={len(result['blockers'])}")
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
