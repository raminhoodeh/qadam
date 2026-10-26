#!/usr/bin/env python3
"""Certify the twelve evidence-fit discovery-micro conversion repairs."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_discovery_micro_certification import (  # noqa: E402
    build_and_write_discovery_micro_certification,
    certification_recovery_class,
)


def main() -> int:
    payload, errors = build_and_write_discovery_micro_certification()
    from orchestrator.runtime.command import report_work_result

    report_work_result(payload, errors)
    print(f"status={payload.get('status')}")
    print(f"checks_passed={payload.get('checks_passed')}/{payload.get('checks_required')}")
    print(f"empirical_recalibration_status={payload.get('empirical_recalibration_status')}")
    print(
        "high_scoring_active_patterns_accounted_for="
        f"{payload.get('acceptance_target', {}).get('high_scoring_active_patterns_accounted_for')}"
    )
    print(
        "paperops_handoff_possible_without_validated_edge="
        f"{payload.get('acceptance_target', {}).get('paperops_handoff_possible_without_validated_edge')}"
    )
    for error in errors:
        print(f"error={error}")
    failure_class = certification_recovery_class(payload, errors)
    if failure_class:
        print(f"qadam_failure_class={failure_class}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
