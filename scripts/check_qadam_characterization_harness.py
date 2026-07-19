#!/usr/bin/env python3
"""Build and validate RF-2 behavior characterization and safety probes."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_characterization_harness import (  # noqa: E402
    CHECK_ARTIFACT,
    CONTRACT_ARTIFACT,
    DASHBOARD_RESULTS_ARTIFACT,
    RESULTS_ARTIFACT,
    SAFETY_RESULTS_ARTIFACT,
    build_and_write_characterization_harness,
)
from orchestrator.qadam_operator_ready_common import read_json, runtime_dir  # noqa: E402


def main() -> int:
    settings = Settings.from_env()
    runtime = runtime_dir(settings)
    bundle, checks, errors = build_and_write_characterization_harness(settings)
    safety = read_json(runtime / SAFETY_RESULTS_ARTIFACT)
    dashboard = bundle["dashboard"]
    print(f"contract_artifact={runtime / CONTRACT_ARTIFACT}")
    print(f"results_artifact={runtime / RESULTS_ARTIFACT}")
    print(f"safety_artifact={runtime / SAFETY_RESULTS_ARTIFACT}")
    print(f"dashboard_artifact={runtime / DASHBOARD_RESULTS_ARTIFACT}")
    print(f"checks_artifact={runtime / CHECK_ARTIFACT}")
    print(f"status={checks['status']}")
    print(f"dashboard_route_count={dashboard.get('route_count')}")
    print(f"dashboard_checker_count={checks['current_dashboard_checker_count']}")
    print(f"superseded_dashboard_checker_count={checks['superseded_dashboard_checker_count']}")
    print(f"negative_probe_count={safety.get('probe_count')}")
    print(f"negative_probe_passed_count={safety.get('passed_probe_count')}")
    print(f"behavior_change_detected={checks['behavior_change_detected']}")
    print(f"broker_write_allowed={checks['authority']['broker_write_allowed']}")
    print(f"live_capital_enabled={checks['authority']['live_capital_enabled']}")
    print(f"validation_error_count={len(errors)}")
    if errors:
        for error in errors:
            print(f"error={error}")
        return 1
    print("qadam_characterization_harness_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
