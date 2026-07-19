#!/usr/bin/env python3
"""Dry-run or explicitly execute the guarded clean-paper-epoch cutover."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_clean_epoch_cutover import (  # noqa: E402
    build_cutover_dry_run,
    execute_clean_epoch_cutover,
)


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--approve-clean-cutover",
        action="store_true",
        help="Explicit operator acknowledgement; has no effect without --execute.",
    )
    return parser.parse_args()


def main() -> int:
    args = _args()
    if args.execute:
        receipt = execute_clean_epoch_cutover(
            operator_approved=args.approve_clean_cutover
        )
        print(f"clean_epoch_cutover_status={receipt['status']}")
        print(f"clean_epoch_id={receipt['paper_epoch_id']}")
        print("clean_epoch_broker_write_count=0")
        return 0
    payload = build_cutover_dry_run()
    readiness = payload["readiness"]
    print(f"clean_epoch_cutover_dry_run_status={payload['status']}")
    print(f"clean_epoch_cutover_ready={str(readiness['cutover_ready']).lower()}")
    print("clean_epoch_cutover_executed=false")
    print("clean_epoch_broker_write_count=0")
    for blocker in readiness.get("blockers", []):
        print(f"clean_epoch_cutover_blocker={blocker}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
