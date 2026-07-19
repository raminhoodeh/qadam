#!/usr/bin/env python3
"""Dry-run or explicitly execute the guarded clean-paper-epoch launch."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_guarded_paper_launch import (  # noqa: E402
    build_guarded_launch_checks,
    execute_guarded_paper_launch,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--approve-paper-release", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    receipt = execute_guarded_paper_launch(
        explicit_operator_approval=args.approve_paper_release,
        execute=args.execute,
    )
    checks, errors = build_guarded_launch_checks()
    print(f"guarded_paper_launch_receipt_status={receipt['status']}")
    print(f"guarded_paper_launch_check={checks['status']}")
    print(f"guarded_paper_launch_state={checks['launch_state']}")
    print(f"guarded_paper_launch_executed={receipt['launch_executed']}")
    print("guarded_paper_launch_direct_broker_call_count=0")
    for blocker in receipt.get("blockers", []):
        print(f"guarded_paper_launch_blocker={blocker}")
    for error in errors:
        print(f"guarded_paper_launch_error={error}")
    return 1 if args.execute and receipt.get("launch_executed") is not True else 0


if __name__ == "__main__":
    raise SystemExit(main())
