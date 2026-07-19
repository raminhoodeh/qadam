#!/usr/bin/env python3
"""Update controlled operator-ready plan state or reviewed amendments."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_dynamic_plan import (  # noqa: E402
    DynamicPlanError,
    apply_reviewed_amendment,
    accept_current_plan_revision_after_explicit_review,
    build_plan_drift,
    initialize_dynamic_plan,
    propose_amendment,
    record_phase_result,
    refresh_dynamic_status,
)
from orchestrator.qadam_operator_ready_common import runtime_dir, write_json_atomic  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--initialize", action="store_true")
    action.add_argument("--from-phase-status", action="store_true")
    action.add_argument("--record-phase")
    action.add_argument("--propose-amendment", action="store_true")
    action.add_argument("--apply-amendment")
    action.add_argument("--accept-current-revision", action="store_true")
    action.add_argument("--check-drift", action="store_true")
    parser.add_argument("--checker-artifact")
    parser.add_argument("--state", choices=["passed", "blocked", "evidence_maturing"])
    parser.add_argument("--evidence-class", default="implementation_and_checks")
    parser.add_argument("--reason", default="")
    parser.add_argument("--target-heading", default="")
    parser.add_argument("--old-text", default="")
    parser.add_argument("--new-text", default="")
    parser.add_argument("--operator-reviewed", action="store_true")
    args = parser.parse_args()
    settings = Settings.from_env()
    try:
        if args.initialize:
            result = initialize_dynamic_plan(settings)
        elif args.from_phase_status:
            result = refresh_dynamic_status(settings)
        elif args.record_phase:
            if not args.checker_artifact:
                parser.error("--record-phase requires --checker-artifact")
            checker_path = Path(args.checker_artifact)
            if not checker_path.is_absolute():
                checker_path = ROOT / checker_path
            result = record_phase_result(
                args.record_phase,
                checker_path,
                settings=settings,
                requested_state=args.state,
                evidence_class=args.evidence_class,
            )
        elif args.propose_amendment:
            result = propose_amendment(
                reason=args.reason,
                target_heading=args.target_heading,
                old_text=args.old_text,
                new_text=args.new_text,
                settings=settings,
            )
        elif args.apply_amendment:
            result = apply_reviewed_amendment(
                args.apply_amendment,
                operator_reviewed=args.operator_reviewed,
                settings=settings,
            )
        elif args.accept_current_revision:
            result = accept_current_plan_revision_after_explicit_review(
                operator_reviewed=args.operator_reviewed,
                reason=args.reason,
                settings=settings,
            )
        else:
            result = build_plan_drift(settings)
            write_json_atomic(
                runtime_dir(settings) / "qadam_operator_ready_plan_drift.json",
                result,
            )
    except DynamicPlanError as exc:
        print("status=blocked")
        print(f"error={exc}")
        return 1
    print(f"status={result.get('status') or result.get('state')}")
    print(f"artifact_type={result.get('artifact_type')}")
    if result.get("evidence_id"):
        print(f"evidence_id={result['evidence_id']}")
    if result.get("proposal_id"):
        print(f"proposal_id={result['proposal_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
