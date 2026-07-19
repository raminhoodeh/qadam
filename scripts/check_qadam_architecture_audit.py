#!/usr/bin/env python3
"""Build and validate the RF-1 no-change architecture audit."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_architecture_audit import (  # noqa: E402
    CHECK_ARTIFACT,
    EDGE_GRAPH_ARTIFACT,
    INVENTORY_ARTIFACT,
    PRODUCER_CONSUMER_ARTIFACT,
    build_and_write_architecture_audit,
)
from orchestrator.qadam_operator_ready_common import runtime_dir  # noqa: E402


def main() -> int:
    settings = Settings.from_env()
    runtime = runtime_dir(settings)
    bundle, checks, errors = build_and_write_architecture_audit(settings)
    inventory = bundle["inventory"]
    edge_graph = bundle["edge_graph"]
    artifacts = bundle["producer_consumer"]
    print(f"inventory_artifact={runtime / INVENTORY_ARTIFACT}")
    print(f"edge_graph_artifact={runtime / EDGE_GRAPH_ARTIFACT}")
    print(f"producer_consumer_artifact={runtime / PRODUCER_CONSUMER_ARTIFACT}")
    print(f"checks_artifact={runtime / CHECK_ARTIFACT}")
    print(f"status={checks['status']}")
    print(f"source_file_count={inventory['source_file_count']}")
    print(f"direct_json_coupling_file_count={inventory['direct_json_coupling_file_count']}")
    print(f"edge_path_stage_count={edge_graph['stage_count']}")
    print(f"local_import_edge_count={edge_graph['local_import_edge_count']}")
    print(f"import_cycle_count={edge_graph['import_cycle_count']}")
    print(f"artifact_count={artifacts['artifact_count']}")
    print(f"multiple_producer_candidate_count={artifacts['multiple_producer_candidate_count']}")
    print(f"broker_write_allowed={checks['authority']['broker_write_allowed']}")
    print(f"validation_error_count={len(errors)}")
    if errors:
        for error in errors:
            print(f"error={error}")
        return 1
    print("qadam_architecture_audit_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
