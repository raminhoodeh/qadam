#!/usr/bin/env python3
"""Run the QSASE certification command bundle."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qsase_end_to_end_certification import (
    build_and_write_qsase_end_to_end_certification,
    validate_negative_qsase_certification_probes,
    validate_qsase_end_to_end_certification,
)


def main() -> int:
    settings = Settings.from_env()
    payload, written, errors = build_and_write_qsase_end_to_end_certification(settings)
    validation_errors = list(errors)
    validation_errors.extend(validate_qsase_end_to_end_certification(payload))
    validation_errors.extend(validate_negative_qsase_certification_probes())

    print(f"artifact={written.get('certification')}")
    print(f"acceptance_report={written.get('acceptance_report')}")
    print(f"status={payload.get('status')}")
    print(f"certified={payload.get('certified')}")
    print(f"passed_phase_count={payload.get('passed_phase_count')}")
    print(f"failed_phase_count={payload.get('failed_phase_count')}")
    print(f"present_artifact_count={payload.get('present_artifact_count')}")
    print(f"required_artifact_count={payload.get('required_artifact_count')}")
    print(f"passed_check_count={payload.get('passed_check_count')}")
    print(f"required_check_count={payload.get('required_check_count')}")
    print(f"failed_check_count={payload.get('failed_check_count')}")
    print(f"authority_violation_count={payload.get('authority_violation_count')}")
    print(f"lineage_gap_count={payload.get('lineage_gap_count')}")
    print(f"dashboard_slop_failure_count={payload.get('dashboard_slop_failure_count')}")
    print(f"telegram_quality_failure_count={payload.get('telegram_quality_failure_count')}")
    print(f"paperops_boundary_failure_count={payload.get('paperops_boundary_failure_count')}")
    print(f"proof_boundary_failure_count={payload.get('proof_boundary_failure_count')}")
    print(f"calendar_boundary_failure_count={payload.get('calendar_boundary_failure_count')}")
    print(f"live_capital_enabled={payload.get('live_capital_enabled')}")
    print(f"broker_write_count={payload.get('broker_write_count')}")
    print(
        "paper_order_created_outside_paperops_count="
        f"{payload.get('paper_order_created_outside_paperops_count')}"
    )
    print(f"proof_credit_allowed={payload.get('proof_credit_allowed')}")
    if validation_errors:
        for error in validation_errors:
            print(f"error={error}")
        print("qsase_certification_check=failed")
        return 1
    print("qsase_certification_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
