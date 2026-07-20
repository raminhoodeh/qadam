#!/usr/bin/env python3
"""Refresh verified IBM usage and the research-only follow-up programme."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_ibm_hardware_utilization import (  # noqa: E402
    RESULT_ARTIFACT,
    VALIDATION_ARTIFACT,
    build_followup_artifact,
    build_utilization_artifact,
    collect_provider_usage,
    validate_followup_artifact,
    validate_utilization_artifact,
    write_artifacts,
)
from orchestrator.qadam_operator_ready_common import read_json  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-dir", default=str(ROOT / "data" / "runtime"))
    parser.add_argument("--refresh-provider-usage", action="store_true")
    args = parser.parse_args()
    runtime = Path(args.runtime_dir)
    generated_at = datetime.now(timezone.utc).isoformat()
    result = read_json(runtime / RESULT_ARTIFACT)
    validation = read_json(runtime / VALIDATION_ARTIFACT)
    if not args.refresh_provider_usage:
        print("ibm_hardware_utilization_status=provider_refresh_required")
        return 2
    provider_usage = collect_provider_usage(runtime)
    utilization = build_utilization_artifact(
        result,
        provider_usage,
        generated_at=generated_at,
    )
    followup = build_followup_artifact(
        result,
        utilization,
        generated_at=generated_at,
        validation=validation,
    )
    outputs = write_artifacts(runtime, utilization, followup)
    errors = [
        *validate_utilization_artifact(utilization),
        *validate_followup_artifact(followup),
    ]
    print(f"ibm_hardware_cost_usd={utilization['cost']['billed_cost']}")
    print(
        "ibm_hardware_provider_turnaround_seconds="
        f"{utilization['timing']['provider_turnaround_seconds']}"
    )
    print(
        "ibm_hardware_quantum_seconds="
        f"{utilization['timing']['ibm_quantum_seconds']}"
    )
    print(f"ibm_hardware_followup_status={followup['status']}")
    print(f"ibm_hardware_followup_candidate_count={followup['candidate_count']}")
    print(f"ibm_hardware_utilization_artifact={outputs['utilization']}")
    print(f"ibm_hardware_followup_artifact={outputs['followup']}")
    print(f"ibm_hardware_utilization_errors={errors}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
