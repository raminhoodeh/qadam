#!/usr/bin/env python3
"""Run one bounded Qadam reliability-critic pass."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_reliability_critic import (  # noqa: E402
    CHECK_ARTIFACT,
    REPAIR_PACKET_ARTIFACT,
    STATUS_ARTIFACT,
    run_reliability_critic,
)
from orchestrator.qadam_operator_ready_common import runtime_dir  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repair", action="store_true")
    parser.add_argument("--verification-wait-seconds", type=float, default=70.0)
    parser.add_argument("--lock-wait-seconds", type=float, default=60.0)
    args = parser.parse_args()
    settings = Settings.from_env()
    payload, errors = run_reliability_critic(
        settings,
        repair=args.repair,
        verification_wait_seconds=max(0.0, args.verification_wait_seconds),
        lock_wait_seconds=max(0.0, args.lock_wait_seconds),
    )
    runtime = runtime_dir(settings)
    print(f"qadam_reliability_critic_status={payload['status']}")
    print(f"qadam_reliability_critic_operating_state={payload['operating_state']}")
    print(f"qadam_reliability_critic_reason={payload['primary_reason']}")
    print(
        "qadam_reliability_critic_verification="
        f"{payload['consecutive_healthy_verification_count']}/2"
    )
    print(f"qadam_reliability_critic_action_count={payload['planned_action_count']}")
    print("qadam_reliability_critic_paper_order_created_count=0")
    print("qadam_reliability_critic_broker_write_count=0")
    print("qadam_reliability_critic_live_capital_enabled=false")
    print(f"artifact={runtime / STATUS_ARTIFACT}")
    print(f"artifact={runtime / REPAIR_PACKET_ARTIFACT}")
    print(f"artifact={runtime / CHECK_ARTIFACT}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors or payload.get("status") != "passed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
