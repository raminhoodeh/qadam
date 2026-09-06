#!/usr/bin/env python3
"""Build and validate EF-5 Akber evidence-fit artifacts."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_akber_evidence_fit import (  # noqa: E402
    build_and_write_akber_evidence_fit,
)


def main() -> int:
    _, checks, errors = build_and_write_akber_evidence_fit()
    from orchestrator.runtime.command import report_work_result
    report_work_result(checks, errors)
    print(f"qadam_akber_evidence_fit_status={checks['status']}")
    print(f"qadam_akber_evidence_fit_profiles={checks['profile_count']}")
    print(f"qadam_akber_evidence_fit_replay_count={checks['profile_replay_count']}")
    print(f"qadam_akber_evidence_fit_ablation_count={checks['profile_ablation_count']}")
    print(f"qadam_akber_evidence_fit_threshold_changes={checks['threshold_change_applied_count']}")
    for error in errors:
        print(f"qadam_akber_evidence_fit_error={error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
