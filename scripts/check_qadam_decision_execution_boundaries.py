#!/usr/bin/env python3
"""Build and validate RF-5 decision and guarded execution boundaries."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_decision_execution_boundaries import (  # noqa: E402
    CHECK_ARTIFACT,
    DECISION_REGISTRY_ARTIFACT,
    EXECUTION_REGISTRY_ARTIFACT,
    ORIGIN_AUDIT_ARTIFACT,
    PAPEROPS_EQUIVALENCE_ARTIFACT,
    build_and_write_decision_execution_boundaries,
)
from orchestrator.qadam_operator_ready_common import runtime_dir  # noqa: E402


def main() -> int:
    settings = Settings.from_env()
    runtime = runtime_dir(settings)
    bundle, checks, errors = build_and_write_decision_execution_boundaries(settings)
    execution = bundle["execution"]
    equivalence = bundle["equivalence"]
    print(f"decision_registry={runtime / DECISION_REGISTRY_ARTIFACT}")
    print(f"execution_registry={runtime / EXECUTION_REGISTRY_ARTIFACT}")
    print(f"paperops_equivalence={runtime / PAPEROPS_EQUIVALENCE_ARTIFACT}")
    print(f"origin_audit={runtime / ORIGIN_AUDIT_ARTIFACT}")
    print(f"checks_artifact={runtime / CHECK_ARTIFACT}")
    print(f"status={checks['status']}")
    print(f"decision_boundary_count={checks['boundary_count']}")
    print(f"paper_gate_count={checks['paper_gate_count']}")
    print(f"canonical_wrapper={execution['canonical_wrapper_command']}")
    print(f"paperops_watch_only_mode={equivalence['paperops_watch_only_mode']}")
    print(f"order_call_count={checks['order_call_count']}")
    print(f"broker_write_count={checks['broker_write_count']}")
    print(f"live_capital_enabled={checks['authority']['live_capital_enabled']}")
    print(f"behavior_changed={checks['behavior_changed']}")
    print(f"validation_error_count={len(errors)}")
    if errors:
        for error in errors:
            print(f"error={error}")
        return 1
    print("qadam_decision_execution_boundaries_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
