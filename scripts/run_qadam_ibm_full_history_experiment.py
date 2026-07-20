#!/usr/bin/env python3
"""Prepare, submit, resume, and verify Qadam's full-history IBM experiment."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_ibm_full_history_experiment import (  # noqa: E402
    poll_full_history_experiment,
    prepare_full_history_experiment,
    submit_full_history_experiment,
    validate_full_history_result,
    wait_for_full_history_experiment,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--prepare", action="store_true")
    action.add_argument("--submit", action="store_true")
    action.add_argument("--poll", action="store_true")
    action.add_argument("--wait", action="store_true")
    parser.add_argument(
        "--operator-approved-single-run",
        action="store_true",
        help="Required for the one-time hardware submission. Creates no recurring authority.",
    )
    parser.add_argument("--poll-interval-seconds", type=int, default=20)
    parser.add_argument("--maximum-wait-seconds", type=int, default=7_200)
    parser.add_argument("--explicit-recovery", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    settings = Settings.from_env()
    if args.prepare:
        prepared = prepare_full_history_experiment(settings)
        manifest = prepared["manifest"]
        hardware = manifest["hardware_manifest"]
        print("ibm_full_history_status=prepared")
        print(
            "ibm_full_history_provider_rows="
            f"{manifest['input_envelope']['provider_backed_historical_row_lineage_count']}"
        )
        print(
            "ibm_full_history_score_rows="
            f"{manifest['input_envelope']['paired_rows_numerically_represented']}"
        )
        print(f"ibm_full_history_prototypes={manifest['batch']['prototype_count']}")
        print(f"ibm_full_history_circuits={hardware['circuit_count']}")
        print(f"ibm_full_history_total_shots={hardware['total_shots']}")
        print("ibm_full_history_hardware_submitted=false")
        return 0
    if args.submit:
        result = submit_full_history_experiment(
            explicit_operator_approval=args.operator_approved_single_run,
            settings=settings,
        )
    elif args.poll:
        result = poll_full_history_experiment(
            settings,
            explicit_recovery=args.explicit_recovery,
        )
    else:
        result = wait_for_full_history_experiment(
            settings,
            poll_interval_seconds=args.poll_interval_seconds,
            maximum_wait_seconds=args.maximum_wait_seconds,
        )
    errors = validate_full_history_result(
        result,
        require_completed=args.wait,
    )
    print(f"ibm_full_history_status={result.get('status')}")
    print(
        "ibm_full_history_hardware_submitted="
        f"{str(result.get('hardware_job_submitted') is True).lower()}"
    )
    print(
        "ibm_full_history_hardware_completed="
        f"{str(result.get('hardware_experiment_completed') is True).lower()}"
    )
    print(
        "ibm_full_history_research_candidate_count="
        f"{result.get('hardware_research_candidate_count', 0)}"
    )
    print(f"ibm_full_history_provider_status={result.get('provider_status')}")
    print(f"ibm_full_history_failure_category={result.get('failure_category')}")
    print(f"ibm_full_history_validation_errors={errors}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
