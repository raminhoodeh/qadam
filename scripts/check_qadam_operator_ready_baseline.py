#!/usr/bin/env python3
"""Build and validate OR-0 canonical runtime truth and safety."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_operator_ready_baseline import (  # noqa: E402
    BASELINE_ARTIFACT,
    CHECK_ARTIFACT,
    PROGRAM_STATUS_ARTIFACT,
    RECONCILIATION_ARTIFACT,
    TRUTH_ARTIFACT,
    build_and_write_operator_ready_baseline,
)
from orchestrator.qadam_operator_ready_common import runtime_dir  # noqa: E402


def main() -> int:
    settings = Settings.from_env()
    runtime = runtime_dir(settings)
    bundle, checks, errors = build_and_write_operator_ready_baseline(settings)
    truth = bundle["truth"]
    reconciliation = bundle["reconciliation"]
    print(f"baseline_artifact={runtime / BASELINE_ARTIFACT}")
    print(f"truth_artifact={runtime / TRUTH_ARTIFACT}")
    print(f"reconciliation_artifact={runtime / RECONCILIATION_ARTIFACT}")
    print(f"program_status_artifact={runtime / PROGRAM_STATUS_ARTIFACT}")
    print(f"checks_artifact={runtime / CHECK_ARTIFACT}")
    print(f"status={checks['status']}")
    print(f"paper_trial={truth['current_paper_trial']['user_facing_name']}")
    for key, value in truth["source_counts"].items():
        if key.endswith("_count"):
            print(f"{key}={value}")
    print(f"runtime_state={reconciliation['status']}")
    print(f"runtime_contradiction_count={reconciliation['contradiction_count']}")
    print(f"paperops_watch_only_mode={reconciliation['research_lock']['paperops_watch_only_mode']}")
    print(f"broker_write_count={checks['broker_write_count']}")
    print(f"live_capital_enabled={checks['authority']['live_capital_enabled']}")
    print(f"validation_error_count={len(errors)}")
    if errors:
        for error in errors:
            print(f"error={error}")
        return 1
    print("qadam_operator_ready_baseline_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
