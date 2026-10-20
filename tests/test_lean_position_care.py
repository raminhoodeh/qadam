from datetime import datetime, timedelta, timezone

from orchestrator.execution.care import full_review_due, handoff_digest
from orchestrator.runtime.services import SERVICE_DEFINITIONS


def test_no_change_path_keeps_position_care_without_research_rebuild():
    now = datetime.now(timezone.utc)
    digest = handoff_digest([{"handoff_id": "one"}])
    summary = {"status": "ready_idle", "generated_at": (now-timedelta(seconds=60)).isoformat(),
               "scheduled_handoff_digest": digest}
    assert not full_review_due(summary, digest, now=now)
    assert not full_review_due({**summary, "status": "ready_actionable"}, digest, now=now)
    assert full_review_due(summary, handoff_digest([{"handoff_id": "two"}]), now=now)
    assert full_review_due(summary, digest, now=now+timedelta(minutes=20))
    assert full_review_due({**summary, "status": "degraded"}, digest, now=now)
    care = next(item for item in SERVICE_DEFINITIONS if item.service_id == "guarded_paperops")
    assert care.cadence_seconds <= 30
    assert care.dependencies == ()
    assert care.command_sequence == (("scripts/run_paperops_autonomous_pass.py", "--scheduled"),)
    assert handoff_digest([{"handoff_id": "one", "generated_at": "changed"}]) == digest
    assert handoff_digest([{"handoff_id": "one", "evidence_digest": "fresh-quote"}]) != digest
