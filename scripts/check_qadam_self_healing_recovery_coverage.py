#!/usr/bin/env python3
"""Fail closed unless every operator service has a safe recovery contract."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_operator_ready_common import validate_authority  # noqa: E402
from orchestrator.qadam_operator_service import (  # noqa: E402
    SERVICE_DEFINITIONS,
    build_and_write_recovery_coverage,
)


def main() -> int:
    payload = build_and_write_recovery_coverage(Settings.from_env())
    errors = list(payload.get("validation_errors") or [])
    if payload.get("status") != "passed":
        errors.append("recovery_coverage_not_passed")
    if int(payload.get("registered_service_count") or 0) != len(SERVICE_DEFINITIONS):
        errors.append("recovery_registry_count_mismatch")
    if int(payload.get("covered_service_count") or 0) != len(SERVICE_DEFINITIONS):
        errors.append("recovery_coverage_incomplete")
    if int(payload.get("uncovered_service_count") or 0) != 0:
        errors.append("uncovered_operator_services_present")
    errors.extend(
        validate_authority(
            payload.get("authority") or {},
            prefix="recovery_coverage_authority",
        )
    )
    errors = sorted(set(errors))
    print(f"qadam_self_healing_recovery_coverage={'passed' if not errors else 'blocked'}")
    print(f"registered_service_count={payload.get('registered_service_count')}")
    print(f"covered_service_count={payload.get('covered_service_count')}")
    print(f"uncovered_service_count={payload.get('uncovered_service_count')}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
