#!/usr/bin/env python3
"""Validate IBM utilization and automatic research follow-up artifacts."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_ibm_hardware_utilization import (  # noqa: E402
    FOLLOWUP_ARTIFACT,
    USAGE_ARTIFACT,
    validate_followup_artifact,
    validate_utilization_artifact,
)
from orchestrator.qadam_operator_ready_common import read_json  # noqa: E402


def main() -> int:
    runtime = ROOT / "data" / "runtime"
    utilization = read_json(runtime / USAGE_ARTIFACT)
    followup = read_json(runtime / FOLLOWUP_ARTIFACT)
    errors = [
        *validate_utilization_artifact(utilization),
        *validate_followup_artifact(followup),
    ]
    if utilization.get("hardware_receipt_hash") != followup.get("hardware_receipt_hash"):
        errors.append("receipt_lineage_mismatch")
    if utilization.get("content_hash") != followup.get("utilization_content_hash"):
        errors.append("utilization_lineage_mismatch")
    print(f"ibm_hardware_utilization_check={'ok' if not errors else 'blocked'}")
    print(f"ibm_hardware_cost_usd={(utilization.get('cost') or {}).get('billed_cost')}")
    print(
        "ibm_hardware_quantum_seconds="
        f"{(utilization.get('timing') or {}).get('ibm_quantum_seconds')}"
    )
    print(f"ibm_hardware_followup_status={followup.get('status')}")
    print(f"ibm_hardware_validation_programs={followup.get('candidate_count')}")
    print(f"ibm_hardware_utilization_errors={sorted(set(errors))}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
