#!/usr/bin/env python3
"""Validate Wave A research authority for Qadam's hybrid quantum loop."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_quantum_edge_governance import (  # noqa: E402
    build_quantum_edge_governance,
    negative_governance_probe_errors,
    validate_quantum_edge_governance,
    write_quantum_edge_governance,
)


def main() -> int:
    payload = build_quantum_edge_governance()
    errors = validate_quantum_edge_governance(payload)
    negative = negative_governance_probe_errors()
    output_path = write_quantum_edge_governance(payload)

    failed_negative_probes = [
        name for name, probe_errors in negative.items() if not probe_errors
    ]

    print(f"quantum_edge_governance_status={payload['status']}")
    print(f"quantum_edge_governance_artifact={output_path}")
    print(
        "quantum_edge_research_candidate_allowed="
        f"{payload['authority']['quantum_research_candidate_allowed']}"
    )
    print(
        "quantum_edge_strategy_creation_allowed="
        f"{payload['authority']['strategy_hypothesis_creation_allowed']}"
    )
    print(
        "quantum_edge_paper_order_allowed="
        f"{payload['authority']['paper_order_allowed']}"
    )
    print(f"quantum_edge_governance_errors={errors}")
    print(f"quantum_edge_negative_probe_failures={failed_negative_probes}")

    if errors or failed_negative_probes:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
