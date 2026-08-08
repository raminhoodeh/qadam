#!/usr/bin/env python3
"""Build and validate the EF-0 immutable baseline."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_evidence_fit_baseline import (  # noqa: E402
    BASELINE_ARTIFACT,
    DRIFT_ARTIFACT,
    OWNERSHIP_ARTIFACT,
    PHASE_STATUS_ARTIFACT,
    build_and_write_evidence_fit_baseline,
)
from orchestrator.qadam_operator_ready_common import runtime_dir  # noqa: E402


def main() -> int:
    runtime = runtime_dir()
    state, status, errors = build_and_write_evidence_fit_baseline()
    for name in (
        BASELINE_ARTIFACT,
        OWNERSHIP_ARTIFACT,
        DRIFT_ARTIFACT,
        PHASE_STATUS_ARTIFACT,
    ):
        print(f"artifact={runtime / name}")
    print(f"status={status['status']}")
    print(f"baseline_id={state['baseline']['baseline_id']}")
    print(f"source_count={state['baseline']['counts']['registered_source_count']}")
    print(f"instrument_count={state['baseline']['counts']['watched_instrument_count']}")
    print(f"validation_error_count={len(errors)}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
