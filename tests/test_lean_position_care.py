from datetime import datetime, timedelta, timezone
import subprocess

import pytest

from orchestrator.execution.care import full_review_due, handoff_digest
from orchestrator.runtime.services import SERVICE_DEFINITIONS
from scripts.run_paperops_autonomous_pass import _position_care_read_failure_class


def test_stale_broker_snapshot_can_recover_without_ignoring_disagreement():
    refresh = subprocess.CompletedProcess([], 0, "", "")
    errors = ["position_care_requires_reconciled_broker_truth"]
    assert _position_care_read_failure_class(
        refresh, {"blockers": ["paper_account_mirror_stale"]}, errors,
    ) == "stale_artifact"
    for blockers in (["position_mismatch"], ["paper_account_mirror_stale", "position_mismatch"], []):
        assert _position_care_read_failure_class(refresh, {"blockers": blockers}, errors) is None
    assert _position_care_read_failure_class(
        refresh, {"blockers": ["paper_account_mirror_stale"]}, ["position_care_failed:ValueError"],
    ) is None


@pytest.mark.parametrize("marker", [
    "credential_operator_action", "safety_violation", "transient_provider_network",
    "storage_maintenance_due", "rate_limit", "code_defect",
])
def test_broker_read_failure_keeps_its_actual_type(marker):
    refresh = subprocess.CompletedProcess([], 1, f"qadam_failure_class={marker}\n", "")
    assert _position_care_read_failure_class(
        refresh, {"blockers": ["read_failed"]}, ["position_care_requires_reconciled_broker_truth"],
    ) == marker


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
    care = next(item for item in SERVICE_DEFINITIONS if item.service_id == "execution_position_care")
    assert care.cadence_seconds <= 30
    assert care.dependencies == ()
    assert care.command_sequence == (("scripts/run_paperops_autonomous_pass.py", "--care-only"),)
    dashboard = next(item for item in SERVICE_DEFINITIONS if item.service_id == "dashboard_refresh")
    assert "paper_state" not in dashboard.read_resources
    assert dashboard.write_resources == ("dashboard_projection",)
    assert handoff_digest([{"handoff_id": "one", "generated_at": "changed"}]) == digest
    assert handoff_digest([{"handoff_id": "one", "evidence_digest": "fresh-quote"}]) != digest
