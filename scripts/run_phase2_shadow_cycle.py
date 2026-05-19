#!/usr/bin/env python3
"""Run Qadam Phase 2 shadow intelligence without execution authority."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.phase2_shadow_cycle import DEFAULT_PHASE2_SOURCES, run_phase2_shadow_cycle  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Phase 2 shadow-intelligence cycle.")
    parser.add_argument("--live-sources", action="store_true", help="Use read-only live source adapters.")
    parser.add_argument("--live-local-llm", action="store_true", help="Call LM Studio chat/completions.")
    parser.add_argument("--events-per-source", type=int, default=3)
    parser.add_argument("--research-limit", type=int, default=8)
    parser.add_argument(
        "--sources",
        default=",".join(DEFAULT_PHASE2_SOURCES),
        help="Comma-separated source keys to include.",
    )
    args = parser.parse_args()

    sources = tuple(source.strip() for source in args.sources.split(",") if source.strip())
    report = run_phase2_shadow_cycle(
        sources=sources,
        live_sources=args.live_sources,
        live_local_llm=args.live_local_llm,
        events_per_source=args.events_per_source,
        research_limit=args.research_limit,
    )

    print(f"phase2_shadow_cycle_status={report['status']}")
    print(f"phase2_shadow_cycle_mode={report['mode']}")
    print(f"phase2_shadow_cycle_live_local_llm={report['live_local_llm']}")
    print(f"phase2_shadow_cycle_source_count={report['source_count']}")
    print(f"phase2_shadow_cycle_queued_packet_count={report['queued_packet_count']}")
    print(f"phase2_shadow_cycle_shadow_signal_count={report['shadow_signal_count']}")
    print(f"phase2_shadow_cycle_local_research_status={report['local_research_status']}")
    print(f"phase2_shadow_cycle_local_research_mode={report['local_research_mode']}")
    print(f"phase2_shadow_cycle_strategy_lead_status={report['strategy_lead_status']}")
    print(f"phase2_shadow_cycle_strategy_lead_execution_allowed={report['strategy_lead_execution_allowed']}")
    print(f"phase2_shadow_cycle_strategy_lead_paper_order_allowed={report['strategy_lead_paper_order_allowed']}")
    print(f"phase2_shadow_cycle_report_path={report['report_path']}")
    print(f"phase2_shadow_cycle_boundary={report['boundary']}")
    for result in report["source_results"]:
        print(
            "phase2_shadow_cycle_source="
            + ",".join(
                [
                    result["source_key"],
                    result["status"],
                    f"events={result['event_count']}",
                    f"queued={result['queued_packet_count']}",
                    f"reason={result['degraded_reason'] or 'none'}",
                ]
            )
        )

    if report["status"] != "ok":
        return 1
    if report["strategy_lead_execution_allowed"] or report["strategy_lead_paper_order_allowed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
