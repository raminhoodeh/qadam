#!/usr/bin/env python3
"""Verify the Wave C strong classical discovery reference lane."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_classical_discovery import run_classical_discovery  # noqa: E402
from orchestrator.qadam_discovery_contract_fixture import (  # noqa: E402
    build_wave_c_contract_fixture_batch,
)
from orchestrator.qadam_quantum_discovery_evidence import (  # noqa: E402
    _runtime_dir,
    _write_json_atomic,
)
from orchestrator.qadam_discovery_backend import validate_discovery_result  # noqa: E402

ARTIFACT = "qadam_classical_discovery_contract.json"


def main() -> int:
    batch = build_wave_c_contract_fixture_batch()
    first = run_classical_discovery(batch)
    second = run_classical_discovery(batch)
    payload = first.to_dict()
    errors = validate_discovery_result(payload)
    deterministic = payload == second.to_dict()
    artifact = _write_json_atomic(_runtime_dir() / ARTIFACT, payload)
    interaction = next(
        item for item in payload["method_results"] if item["method"] == "depth_two_tree_interaction"
    )

    print(f"classical_discovery_artifact={artifact}")
    print(f"classical_discovery_manifest_hash={payload['shared_manifest_hash']}")
    print(f"classical_discovery_method_count={len(payload['method_results'])}")
    print(f"classical_discovery_candidate_count={len(payload['research_candidates'])}")
    print(f"classical_discovery_detected_pair={interaction['feature_pair']}")
    print(f"classical_discovery_deterministic={deterministic}")
    print(f"classical_discovery_contract_fixture_only={payload['contract_fixture_only']}")
    print(f"classical_discovery_validated_edge_created={payload['validated_edge_created']}")
    print(f"classical_discovery_paper_order_created={payload['paper_order_created']}")
    print(f"classical_discovery_errors={errors}")
    return 0 if deterministic and not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
