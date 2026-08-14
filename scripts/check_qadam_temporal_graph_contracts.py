#!/usr/bin/env python3
"""Check QEG-1 temporal, provenance and authority contracts."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_qeg_common import write_phase_status
from orchestrator.qadam_temporal_graph_contracts import (
    build_edge,
    build_node,
    validate_negative_probes,
    validate_record,
)


if __name__ == "__main__":
    node = build_node(
        "source_observation", "contract-check", layer="observed",
        evidence_state="provider_backed", payload={"provider": "contract-check"},
    )
    edge = build_edge(
        "reported_by", node["node_id"], node["node_id"], layer="observed",
        evidence_state="provider_backed", payload={"self_test": True},
    )
    errors = [*validate_record(node), *validate_record(edge), *validate_negative_probes()]
    write_phase_status(
        "QEG-1", status="passed" if not errors else "blocked",
        implementation_complete=not errors, empirical_state="contract_self_tested",
        artifacts=[], blockers=errors,
    )
    print(f"validation_error_count={len(errors)}")
    for error in errors:
        print(f"error={error}")
    raise SystemExit(1 if errors else 0)
