#!/usr/bin/env python3
"""Probe OR-1 single-instance and atomic-state behavior in a temp store."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_canonical_contracts import AtomicArtifactStore  # noqa: E402
from orchestrator.qadam_operator_ready_common import authority_flags, now_iso, runtime_dir  # noqa: E402
from orchestrator.qadam_research_supervisor import (  # noqa: E402
    ATOMICITY_CHECK_ARTIFACT,
    ResearchSupervisor,
    build_job,
)


def main() -> int:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="qadam-or1-atomic-") as name:
        path = Path(name)
        supervisor = ResearchSupervisor(path, lease_ttl_seconds=60)
        job = build_job(
            job_type="price_acquisition",
            provider="test-provider",
            instrument="TEST",
            date_partition="2026-01",
            requested_granularity="1d",
        ).to_dict()
        supervisor.write_jobs([job])
        first, _ = supervisor.acquire_lease(owner_pid=999_999_991)
        second, second_reason = supervisor.acquire_lease(owner_pid=999_999_992)
        if first is not True or second is not False or second_reason != "active_lease_exists":
            errors.append("single_instance_lease_probe_failed")
        store = AtomicArtifactStore(path)
        store.write_json("atomic.json", {"version": 1})
        (path / ".atomic.json.interrupted.tmp").write_text('{"version":', encoding="utf-8")
        if json.loads((path / "atomic.json").read_text(encoding="utf-8")) != {"version": 1}:
            errors.append("interrupted_temp_write_corrupted_state")
        if len(supervisor.load_jobs()) != 1:
            errors.append("manifest_atomic_read_failed")
    payload = {
        "schema_version": "qadam_research_supervisor.v1",
        "artifact_type": "qadam_research_state_atomicity_checks",
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "single_instance_probe_passed": "single_instance_lease_probe_failed" not in errors,
        "interrupted_write_probe_passed": "interrupted_temp_write_corrupted_state" not in errors,
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    AtomicArtifactStore(runtime_dir()).write_json(ATOMICITY_CHECK_ARTIFACT, payload)
    print(f"status={payload['status']}")
    print(f"validation_error_count={len(errors)}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
