#!/usr/bin/env python3
"""Build and validate the public-safe Qadam 10-stage lifecycle."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_end_to_end_lifecycle import (  # noqa: E402
    CHECK_ARTIFACT,
    CONTRACT_ARTIFACT,
    ROUTE_MAP_ARTIFACT,
    SUMMARY_ARTIFACT,
    validate_lifecycle_contract,
    validate_lifecycle_summary,
)
from orchestrator.qadam_operator_dashboard import (  # noqa: E402
    build_and_write_operator_dashboard,
)
from orchestrator.qadam_operator_ready_common import runtime_dir  # noqa: E402


def main() -> int:
    settings = Settings.from_env()
    runtime = runtime_dir(settings)
    state, _checks, _operator_errors = build_and_write_operator_dashboard(settings)
    errors = [
        *validate_lifecycle_contract(state["lifecycle_contract"]),
        *validate_lifecycle_summary(state["lifecycle_dashboard"]),
    ]
    lifecycle_checks = runtime / CHECK_ARTIFACT
    for name in (
        CONTRACT_ARTIFACT,
        ROUTE_MAP_ARTIFACT,
        SUMMARY_ARTIFACT,
        CHECK_ARTIFACT,
    ):
        print(f"artifact={runtime / name}")
    print(f"status={'passed' if not errors else 'blocked'}")
    print(f"stage_count={state['lifecycle_contract']['stage_count']}")
    print(f"route_count={state['lifecycle_contract']['route_count']}")
    print("single_global_current_stage=False")
    print("dashboard_read_only=True")
    print("paper_order_created_count=0")
    print("broker_write_count=0")
    print(f"check_artifact_exists={lifecycle_checks.exists()}")
    print(f"validation_error_count={len(errors)}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
