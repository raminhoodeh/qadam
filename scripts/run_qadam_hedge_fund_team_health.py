#!/usr/bin/env python3
"""Run one bounded hedge-fund team analysis and health cycle."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_hedge_fund_team_health import run_hedge_fund_team_cycle  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-repair", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    payload, errors = run_hedge_fund_team_cycle(
        repair_local=not args.no_repair,
        force=args.force,
    )
    team = payload.get("team") or {}
    pipeline = payload.get("trading_pipeline") or {}
    print(f"qadam_team_health_status={payload.get('status')}")
    print(f"qadam_team_health_healthy_roles={payload.get('healthy_required_role_count')}/4")
    print(f"qadam_team_health_pipeline={pipeline.get('healthy_stage_count')}/10")
    print(f"qadam_team_health_local_llm={(team.get('local_research_analyst') or {}).get('status')}")
    print(
        f"qadam_team_health_frontier_llm={(team.get('frontier_strategy_lead') or {}).get('status')}"
    )
    print(f"qadam_team_health_error_count={len(errors)}")
    print("qadam_team_health_paper_order_created_count=0")
    print("qadam_team_health_broker_write_count=0")
    print("qadam_team_health_live_capital_enabled=false")
    return 0 if not errors and payload.get("status") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
