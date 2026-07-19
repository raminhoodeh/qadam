#!/usr/bin/env python3
"""Probe exactly-once resumability for OR-1 research jobs."""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_canonical_contracts import AtomicArtifactStore  # noqa: E402
from orchestrator.qadam_operator_ready_common import authority_flags, now_iso, runtime_dir  # noqa: E402
from orchestrator.qadam_research_supervisor import (  # noqa: E402
    RESUME_CHECK_ARTIFACT,
    ResearchSupervisor,
    build_job,
)


def main() -> int:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="qadam-or1-resume-") as name:
        supervisor = ResearchSupervisor(Path(name))
        job = build_job(
            job_type="source_acquisition",
            source="test-source",
            provider="test-provider",
            date_partition="2026-01-01",
            requested_granularity="event",
            status="interrupted",
        ).to_dict()
        job["resume_cursor"] = "cursor-17"
        supervisor.write_jobs([job, dict(job)])
        supervisor.write_checkpoint(
            current_job_id=job["job_id"],
            resume_cursor="cursor-17",
            reason="termination_probe",
        )
        resumable = supervisor.resumable_jobs()
        if len(resumable) != 1:
            errors.append("resume_job_not_exactly_once")
        elif resumable[0].get("resume_cursor") != "cursor-17":
            errors.append("resume_cursor_not_preserved")
    payload = {
        "schema_version": "qadam_research_supervisor.v1",
        "artifact_type": "qadam_research_resume_checks",
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "resumes_only_incomplete_idempotent_jobs": True,
        "execution_action_resume_allowed": False,
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    AtomicArtifactStore(runtime_dir()).write_json(RESUME_CHECK_ARTIFACT, payload)
    print(f"status={payload['status']}")
    print(f"validation_error_count={len(errors)}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
