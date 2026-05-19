#!/usr/bin/env python3
"""Validate that Phase 2 consumes paper-account context without authority."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.phase2_shadow_cycle import run_phase2_shadow_cycle  # noqa: E402
from orchestrator.strategy_lead import StrategyLeadShadowStore  # noqa: E402


def main() -> int:
    settings = Settings.from_env()
    report = run_phase2_shadow_cycle(
        sources=("fred", "alpaca"),
        live_sources=False,
        live_local_llm=False,
        events_per_source=2,
        research_limit=5,
        settings=settings,
    )
    if report["status"] != "ok":
        print(f"phase2_paper_context_status={report['status']}")
        return 1
    if report["paper_account_write_authority"] is not False:
        print("phase2_paper_context_write_authority_enabled=true")
        return 1
    if report["paper_account_live_capital_enabled"] is not False:
        print("phase2_paper_context_live_capital_enabled=true")
        return 1
    if report["local_research_execution_allowed"] is not False:
        print("phase2_paper_context_local_execution_allowed=true")
        return 1
    if report["local_research_paper_order_allowed"] is not False:
        print("phase2_paper_context_local_paper_order_allowed=true")
        return 1
    if report["strategy_lead_execution_allowed"] is not False:
        print("phase2_paper_context_strategy_execution_allowed=true")
        return 1
    if report["strategy_lead_paper_order_allowed"] is not False:
        print("phase2_paper_context_strategy_paper_order_allowed=true")
        return 1

    packets = StrategyLeadShadowStore(settings=settings).read()
    strategy_packet = next(
        (packet for packet in reversed(packets) if packet.get("packet_id") == report["strategy_lead_packet_id"]),
        {},
    )
    paper_context = strategy_packet.get("paper_account_context", {})
    if not paper_context:
        print("phase2_paper_context_strategy_context_missing=true")
        return 1
    if paper_context.get("execution_allowed") is not False or paper_context.get("paper_order_allowed") is not False:
        print("phase2_paper_context_strategy_context_authority_enabled=true")
        return 1
    if paper_context.get("write_authority") is not False or paper_context.get("live_capital_enabled") is not False:
        print("phase2_paper_context_strategy_context_write_enabled=true")
        return 1
    if "read-only" not in paper_context.get("boundary", ""):
        print("phase2_paper_context_strategy_boundary_weak=true")
        return 1

    print("phase2_paper_context_check=ok")
    print(f"phase2_paper_context_status={report['paper_account_context_status']}")
    print(f"phase2_paper_context_connection_status={report['paper_account_connection_status']}")
    print(f"phase2_paper_context_current_balance_gbp={report['paper_account_current_balance_gbp']}")
    print(f"phase2_paper_context_order_count={report['paper_account_order_count']}")
    print(f"phase2_paper_context_open_position_count={report['paper_account_open_position_count']}")
    print(f"phase2_paper_context_strategy_packet_id={report['strategy_lead_packet_id']}")
    print("phase2_paper_context_boundary=paper-account context is read-only and non-executable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
