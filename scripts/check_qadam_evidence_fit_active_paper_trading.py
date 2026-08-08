#!/usr/bin/env python3
"""Run the EF-10 fail-closed evidence-fit certification."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_evidence_fit_baseline import (  # noqa: E402
    write_evidence_fit_phase_status,
)
from orchestrator.qadam_evidence_fit_certification import (  # noqa: E402
    CERTIFICATION_ARTIFACT,
    build_and_write_evidence_fit_certification,
)
from orchestrator.qadam_evidence_fit_visibility import (  # noqa: E402
    CHECK_ARTIFACT as VISIBILITY_CHECK_ARTIFACT,
    DASHBOARD_ARTIFACT,
    FUNNEL_ARTIFACT,
    MATERIAL_CHANGES_ARTIFACT,
    NOTIFICATION_CANDIDATES_ARTIFACT,
    build_and_write_evidence_fit_visibility,
)


def main() -> int:
    _visibility, visibility_checks, visibility_errors = (
        build_and_write_evidence_fit_visibility()
    )
    write_evidence_fit_phase_status(
        {
            "EF-9": {
                "errors": visibility_errors,
                "checks": {
                    "status": visibility_checks.get("status"),
                    "dashboard_area_count": visibility_checks.get(
                        "dashboard_area_count"
                    ),
                    "notification_status": visibility_checks.get(
                        "notification_status"
                    ),
                },
                "output_artifacts": [
                    DASHBOARD_ARTIFACT,
                    FUNNEL_ARTIFACT,
                    MATERIAL_CHANGES_ARTIFACT,
                    NOTIFICATION_CANDIDATES_ARTIFACT,
                    VISIBILITY_CHECK_ARTIFACT,
                ],
            }
        }
    )
    certification, certification_errors = (
        build_and_write_evidence_fit_certification()
    )
    errors = [*visibility_errors, *certification_errors]
    phase_status = write_evidence_fit_phase_status(
        {
            "EF-10": {
                "errors": errors,
                "checks": {
                    "status": certification.get("status"),
                    "check_count": certification.get("check_count"),
                    "passed_check_count": certification.get(
                        "passed_check_count"
                    ),
                    "negative_probe_count": certification.get(
                        "negative_probe_count"
                    ),
                    "passed_negative_probe_count": certification.get(
                        "passed_negative_probe_count"
                    ),
                },
                "output_artifacts": [CERTIFICATION_ARTIFACT],
            }
        }
    )
    print(f"artifact={ROOT / 'data' / 'runtime' / CERTIFICATION_ARTIFACT}")
    print(f"status={certification['status']}")
    print(f"passed_checks={certification['passed_check_count']}/{certification['check_count']}")
    print(
        "passed_negative_probes="
        f"{certification['passed_negative_probe_count']}/"
        f"{certification['negative_probe_count']}"
    )
    print(
        "certified_for_autonomous_paper_observation="
        f"{certification['certified_for_autonomous_paper_observation']}"
    )
    print(
        "implemented_through_phase="
        f"{phase_status.get('implemented_through_phase')}"
    )
    for error in errors:
        print(f"error={error}")
    return 0 if not errors and phase_status.get("status") == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
