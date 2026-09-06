#!/usr/bin/env python3
"""Run one bounded qualitative evidence operator cycle."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_agent_reach_operator import run_agent_reach_operator  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument(
        "--no-fast-path",
        action="store_true",
        help="Produce upstream evidence only; leave canonical compilation to its owner service.",
    )
    args = parser.parse_args()
    payload, errors = run_agent_reach_operator(
        allow_network=args.allow_network,
        run_fast_path=not args.no_fast_path,
    )
    from orchestrator.runtime.command import report_work_result
    report_work_result(payload, errors)
    print(f"status={payload.get('status')}")
    print(f"pipeline_status={payload.get('pipeline_status')}")
    print(f"resource_state={payload.get('resource_state')}")
    for error in errors:
        print(f"error={error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
