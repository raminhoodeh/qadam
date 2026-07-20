#!/usr/bin/env python3
"""Run the no-provider historical test for the IBM hardware relationship."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_ibm_hardware_candidate_validation import (  # noqa: E402
    build_and_write_hardware_candidate_validation,
)


def main() -> int:
    payload, checks, errors = build_and_write_hardware_candidate_validation()
    verdict = payload.get("verdict") or {}
    comparison = payload.get("comparison") or {}
    print(f"ibm_hardware_candidate_validation_status={payload.get('status')}")
    print(
        "ibm_hardware_candidate_historical_survivor="
        f"{verdict.get('historical_survivor')}"
    )
    print(
        "ibm_hardware_candidate_incremental_mean_net_return="
        f"{comparison.get('interaction_minus_baseline_mean_net_return_per_opportunity')}"
    )
    print(
        "ibm_hardware_candidate_adjusted_p_value="
        f"{comparison.get('multiple_testing_adjusted_p_value')}"
    )
    print(f"ibm_hardware_candidate_next_action={verdict.get('next_action')}")
    print(f"ibm_hardware_candidate_checks={checks.get('status')}")
    print(f"ibm_hardware_candidate_errors={errors}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
