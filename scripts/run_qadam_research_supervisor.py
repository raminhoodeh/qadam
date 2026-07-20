#!/usr/bin/env python3
"""Run one safe supervisor cycle, including OR-13 no-order shadow observation."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_forward_shadow import build_and_write_forward_shadow  # noqa: E402
from orchestrator.qadam_operator_ready_common import runtime_dir  # noqa: E402
from orchestrator.qadam_research_supervisor import (  # noqa: E402
    ResearchSupervisor,
    append_job_event,
    build_and_write_research_supervisor,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--once", action="store_true", help="Acquire, checkpoint, and release once."
    )
    parser.add_argument("--status", action="store_true", help="Refresh readiness artifacts only.")
    parser.add_argument(
        "--allow-shadow-network",
        action="store_true",
        help="Allow read-only provider prices for eligible forward-shadow signals.",
    )
    args = parser.parse_args()
    if not args.once and not args.status:
        parser.error("choose --once or --status; background installation is explicit")
    settings = Settings.from_env()
    runtime = runtime_dir(settings)
    status, checks, errors = build_and_write_research_supervisor(settings)
    if errors or args.status:
        print(f"status={checks['status']}")
        return 1 if errors else 0
    if status.get("superseded_by_operator_service") is True:
        print("status=passed")
        print("runtime_state=superseded_by_operator_service")
        print("scheduler_owner=qadam_operator_service")
        print("duplicate_research_cycle_started=false")
        return 0
    supervisor = ResearchSupervisor(runtime)
    acquired, reason = supervisor.acquire_lease()
    if not acquired:
        print("status=blocked")
        print(f"reason={reason}")
        return 1
    try:
        shadow_job_id = "forward-shadow-observation"
        append_job_event(
            runtime,
            event="control_cycle_started",
            job_id=shadow_job_id,
            detail="OR-13 read-only no-order shadow observation",
        )
        supervisor.write_heartbeat(
            state="working",
            current_phase="OR-13",
            service_id="continuous_forward_shadow",
            current_job_id=shadow_job_id,
        )
        shadow_bundle, shadow_checks, shadow_errors = build_and_write_forward_shadow(
            settings,
            allow_network=args.allow_shadow_network,
            supervised_cycle=True,
        )
        supervisor.write_heartbeat(
            state="idle_ready",
            current_phase="OR-13",
            service_id="continuous_forward_shadow",
            current_job_id=None,
            processed_units=(len(shadow_bundle["decisions"]) + len(shadow_bundle["outcomes"])),
        )
        supervisor.write_checkpoint(
            current_job_id=None, resume_cursor=None, reason="one_shot_control_cycle"
        )
        append_job_event(
            runtime,
            event="forward_shadow_cycle_completed",
            job_id=shadow_job_id,
            detail=(
                f"status={shadow_checks['status']}; decisions={shadow_checks['decision_count']}; "
                f"outcomes={shadow_checks['outcome_count']}"
            ),
        )
    finally:
        supervisor.release_lease(reason="one_shot_complete")
    print("status=passed" if not shadow_errors else "status=blocked")
    print(f"runtime_state={status['status']}")
    print(f"forward_shadow_state={shadow_checks['service_state']}")
    print(f"forward_shadow_evidence_state={shadow_checks['status']}")
    return 1 if shadow_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
