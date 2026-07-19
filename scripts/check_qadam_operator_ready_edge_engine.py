#!/usr/bin/env python3
"""Run OR-19 fail-closed operator-ready certification."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_operator_ready_certification import (  # noqa: E402
    CERTIFICATION_ARTIFACT,
    CHECK_ARTIFACT,
    build_and_write_operator_ready_certification,
)
from orchestrator.qadam_operator_ready_common import runtime_dir  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    settings = Settings.from_env()
    runtime = runtime_dir(settings)
    certification, checks, errors = build_and_write_operator_ready_certification(
        settings, mode="preflight" if args.preflight else "full"
    )
    print(f"artifact={runtime / CERTIFICATION_ARTIFACT}")
    print(f"checks_artifact={runtime / CHECK_ARTIFACT}")
    for key in (
        "status",
        "checker_implementation_ready",
        "certification_state",
        "certification_passed",
        "research_operational",
        "edge_validated",
        "paper_operator_ready",
        "paper_performance_proven",
        "passed_group_count",
        "blocked_group_count",
        "blocker_count",
        "paper_trial_resume_allowed",
        "research_lock_release_performed",
        "existence_only_credit_count",
        "paper_order_created_count",
        "broker_write_count",
        "proof_credit_created_count",
    ):
        print(f"{key}={checks[key]}")
    for blocker in certification.get("top_blockers", []):
        print(f"blocker={blocker['group']}:{blocker['check_id']}:{blocker['reason']}")
    print(f"validation_error_count={len(errors)}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
