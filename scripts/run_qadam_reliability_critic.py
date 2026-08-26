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
from orchestrator.qadam_hedge_fund_team_health import (  # noqa: E402
    run_hedge_fund_team_cycle,
    send_team_health_telegram_update,
)
from orchestrator.qadam_operator_ready_common import runtime_dir  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repair", action="store_true")
    parser.add_argument("--verification-wait-seconds", type=float, default=70.0)
    parser.add_argument("--lock-wait-seconds", type=float, default=60.0)
    parser.add_argument("--skip-team-cycle", action="store_true")
    parser.add_argument("--force-team-cycle", action="store_true")
    parser.add_argument("--skip-telegram", action="store_true")
    args = parser.parse_args()
    settings = Settings.from_env()
    team_payload: dict = {}
    team_errors: list[str] = []
    if not args.skip_team_cycle:
        team_payload, team_errors = run_hedge_fund_team_cycle(
            settings,
            repair_local=args.repair,
            force=args.force_team_cycle,
        )
    payload, errors = run_reliability_critic(
        settings,
        repair=args.repair,
        verification_wait_seconds=max(0.0, args.verification_wait_seconds),
        lock_wait_seconds=max(0.0, args.lock_wait_seconds),
    )
    telegram = {"status": "skipped", "sent": False}
    if not args.skip_telegram and team_payload:
        telegram = send_team_health_telegram_update(team_payload, payload, settings)
    runtime = runtime_dir(settings)
    print(f"qadam_team_health_status={team_payload.get('status', 'skipped')}")
    print(
        "qadam_team_health_roles="
        f"{team_payload.get('healthy_required_role_count', 0)}/"
        f"{team_payload.get('required_role_count', 4)}"
    )
    print(
        "qadam_team_health_pipeline="
        f"{(team_payload.get('trading_pipeline') or {}).get('healthy_stage_count', 0)}/10"
    )
    print(f"qadam_team_health_telegram_status={telegram.get('status')}")
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
    for error in [*team_errors, *errors]:
        print(f"error={error}")
    return 1 if team_errors or errors or payload.get("status") != "passed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
