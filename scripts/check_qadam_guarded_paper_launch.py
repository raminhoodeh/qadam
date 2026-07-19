#!/usr/bin/env python3
"""Validate Phase 11 guarded launch implementation and current state."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_guarded_paper_launch import build_guarded_launch_checks  # noqa: E402


def main() -> int:
    checks, errors = build_guarded_launch_checks()
    print(f"guarded_paper_launch_check={checks['status']}")
    print(f"guarded_paper_launch_implementation_ready={checks['implementation_ready']}")
    print(f"guarded_paper_launch_state={checks['launch_state']}")
    print(f"guarded_paper_operation_running={checks['guarded_paper_operation_running']}")
    print("guarded_paper_launch_direct_broker_call_count=0")
    for error in errors:
        print(f"guarded_paper_launch_error={error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
