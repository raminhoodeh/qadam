#!/usr/bin/env python3
"""Verify the Wave B shared classical/quantum discovery manifest."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_quantum_discovery_evidence import (  # noqa: E402
    build_point_in_time_foundation,
)
from orchestrator.qadam_quantum_discovery_manifest import (  # noqa: E402
    build_shared_manifest_contract,
    validate_shared_manifest_contract,
    write_shared_manifest_contract,
)


def main() -> int:
    evidence = build_point_in_time_foundation()
    contract = build_shared_manifest_contract(
        empirical_evidence_ready=evidence["empirical_evidence_ready"],
        empirical_blockers=evidence["blockers"],
    )
    errors = validate_shared_manifest_contract(contract)
    artifact = write_shared_manifest_contract(contract)
    window = contract["contract_fixture_window"]

    print(f"quantum_manifest_status={contract['status']}")
    print(f"quantum_manifest_artifact={artifact}")
    print(
        "quantum_manifest_implementation_ready="
        f"{contract['implementation_contract_ready']}"
    )
    print(f"quantum_manifest_empirical_ready={contract['empirical_manifest_ready']}")
    print(f"quantum_manifest_empirical_blockers={contract['empirical_blockers']}")
    print(f"quantum_manifest_hash={window['manifest_hash']}")
    print(
        "quantum_manifest_lane_hash_equal="
        f"{contract['classical_quantum_manifest_hash_equal']}"
    )
    print(f"quantum_manifest_deterministic={contract['deterministic_rebuild_passed']}")
    print(f"quantum_manifest_labels_present={window['labels_present']}")
    print(f"quantum_manifest_hardware_job_authorized={contract['hardware_job_authorized']}")
    print(f"quantum_manifest_errors={errors}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
