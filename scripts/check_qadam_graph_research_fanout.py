#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_graph_research_fanout import build_research_fanout, validate_proposed_delta


if __name__ == "__main__":
    payload, errors = build_research_fanout()
    negative = validate_proposed_delta(
        {"source_node_ids": ["fabricated"], "governed_write_requested": True},
        {"source_feed:known"},
    )
    if not {"proposal_citation_unknown", "proposal_governed_write_forbidden"}.issubset(set(negative)):
        errors.append("fanout_negative_probe_failed")
    print(f"task_count={payload['task_count']}")
    print(f"research_round_count={payload['research_round_count']}")
    print(f"validation_error_count={len(errors)}")
    for error in errors:
        print(f"error={error}")
    raise SystemExit(1 if errors else 0)
