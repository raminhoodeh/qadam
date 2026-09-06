#!/usr/bin/env python3
"""Run one safe, no-order forward-shadow observation cycle."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_forward_shadow import build_and_write_forward_shadow  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run exactly one research-only observation cycle.",
    )
    parser.add_argument(
        "--allow-network",
        action="store_true",
        help="Allow read-only market-data calls for eligible shadow signals.",
    )
    args = parser.parse_args()
    if not args.once:
        parser.error("--once is required; process supervision belongs to the Qadam operator service")
    settings = Settings.from_env()
    operator_dispatch = os.environ.get("QADAM_OPERATOR_DISPATCH") == "1"
    _bundle, checks, errors = build_and_write_forward_shadow(
        settings,
        allow_network=args.allow_network,
        supervised_cycle=operator_dispatch,
    )
    from orchestrator.runtime.command import report_work_result
    report_work_result(checks, errors)
    print(f"status={checks['status']}")
    print(f"service_state={checks['service_state']}")
    print(f"decision_count={checks['decision_count']}")
    print(f"outcome_count={checks['outcome_count']}")
    print(f"phase_acceptance_ready={checks['phase_acceptance_ready']}")
    print(
        "supervisor_heartbeat_proves_shadow_cycle="
        f"{checks['supervisor_heartbeat_proves_shadow_cycle']}"
    )
    print("paper_order_created_count=0")
    print("proof_credit_count=0")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
