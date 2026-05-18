#!/usr/bin/env python3
"""Check the Phase 2 local Research Analyst inference contract."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.intelligence import (  # noqa: E402
    local_research_analyst_status,
    run_local_research_analyst_inference,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local Research Analyst shadow assessment checks.")
    parser.add_argument("--live", action="store_true", help="Call LM Studio chat/completions.")
    parser.add_argument("--limit", type=int, default=5, help="Queued shadow packets to include.")
    args = parser.parse_args()

    before = local_research_analyst_status()
    result = run_local_research_analyst_inference(limit=args.limit, live=args.live)
    assessment = result.get("assessment", {})
    store = result["store"]

    print(f"local_research_status={result['status']}")
    print(f"local_research_mode={result['mode']}")
    print(f"local_research_provider={before['provider']}")
    print(f"local_research_model={before['model']}")
    print(f"local_research_processed_packet_count={result.get('processed_packet_count', 0)}")
    print(f"local_research_store_status={store['status']}")
    print(f"local_research_assessment_count={store['assessment_count']}")
    print(f"local_research_execution_allowed_count={store['execution_allowed_count']}")
    print(f"local_research_paper_order_allowed_count={store['paper_order_allowed_count']}")
    print(f"local_research_escalation={assessment.get('escalation_recommendation', 'none')}")
    print(f"local_research_boundary={result['boundary']}")

    if args.live and result["status"] != "ok":
        print(f"local_research_live_reason={result.get('reason', 'unknown')}")
        print(f"local_research_live_detail={result.get('detail', 'none')}")
        return 1
    if store["status"] != "ok":
        return 1
    if store["execution_allowed_count"] != 0 or store["paper_order_allowed_count"] != 0:
        return 1
    if result["status"] != "ok":
        return 1

    print("local_research_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
