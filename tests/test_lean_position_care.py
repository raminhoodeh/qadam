from datetime import datetime, timedelta, timezone
from dataclasses import replace
import json
import subprocess
from types import SimpleNamespace

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


@pytest.mark.parametrize("arguments", [[], ["--scheduled"]])
def test_stale_care_read_stops_before_any_entry_review(tmp_path, monkeypatch, capsys, arguments):
    from scripts import run_paperops_autonomous_pass as runner
    lease = SimpleNamespace(environment=lambda: {})
    ledger = SimpleNamespace(
        store=SimpleNamespace(read_table=lambda *_: [{}]),
        acquire_execution_owner=lambda *a, **k: lease,
        release_execution_owner=lambda *_: None,
    )
    keeper = SimpleNamespace(stop=lambda: None)
    monkeypatch.setattr(runner.sys, "argv", ["paperops", *arguments])
    monkeypatch.setattr(runner, "Settings", SimpleNamespace(
        from_env=lambda: SimpleNamespace(runtime_dir=str(tmp_path))))
    monkeypatch.setattr(runner, "_acquire_pass_lock", lambda *_: SimpleNamespace(close=lambda: None))
    monkeypatch.setattr(runner, "OperatingLedger", lambda *_: ledger)
    monkeypatch.setattr("orchestrator.execution.contract.bind_execution_contract", lambda *a, **k: None)
    monkeypatch.setattr("orchestrator.execution.contract.require_execution_contract", lambda *a, **k: None)
    monkeypatch.setattr("orchestrator.execution.ownership.ExecutionLeaseKeeper",
                        lambda *a: SimpleNamespace(start=lambda: keeper))
    monkeypatch.setattr("orchestrator.runtime.availability.record_care_sample", lambda *a, **k: None)
    monkeypatch.setattr(runner, "_refresh_and_reconcile_paper_mirror", lambda *a, **k: (
        subprocess.CompletedProcess([], 0, "", ""),
        {"status": "blocked", "blockers": ["paper_account_mirror_stale"]},
    ))
    monkeypatch.setattr(runner, "build_and_write_router_v3", lambda *_: pytest.fail("Entry review must not run"))
    monkeypatch.setattr("orchestrator.execution.care.full_review_due",
                        lambda *a, **k: pytest.fail("Known stale care read must stop first"))
    reported = []
    monkeypatch.setattr("orchestrator.runtime.command.report_work_result", lambda *a: reported.append(a))
    assert runner.main() == 1
    assert "qadam_failure_class=stale_artifact" in capsys.readouterr().out
    assert reported[-1][0]["entry_review_invoked"] is False
    assert reported[-1][0]["new_entry_submission_count"] == 0


def test_position_care_circuit_requires_exact_route_and_three_verified_passes(tmp_path, monkeypatch):
    from orchestrator.runtime import operator as op
    monkeypatch.setattr(op, "runtime_dir", lambda *_: tmp_path)
    monkeypatch.setattr(op, "_service_revalidation_identity", lambda *_: "reviewed-care-build")
    (tmp_path / op.CIRCUIT_BREAKERS_ARTIFACT).write_text(json.dumps({"services": {
        "execution_position_care": {"state": "open", "failure_class": "stale_artifact"},
    }}))
    with pytest.raises(ValueError, match="not_permitted"):
        op.repair_operator_service_circuit("execution_position_care")
    passes = []

    def execute(definition, **kwargs):
        passes.append(definition.command_sequence)
        return {"state": "completed", "duration_seconds": 1, "command_results": [],
                "generation_ids": {}, "input_generation_ids": {},
                "input_generation_binding_complete": True, "mixed_generation_join_count": 0}

    monkeypatch.setattr(op, "_execute_service_synchronously", execute)
    result = op.repair_operator_service_circuit(
        "execution_position_care", explicit_position_care_confirmation=True,
    )
    assert result["status"] == "repaired"
    assert result["verification_pass_count"] == 3
    assert result["explicit_position_care_confirmation"] is True
    assert passes == [(("scripts/run_paperops_autonomous_pass.py", "--care-only"),)] * 3
    assert op._circuit_breaker_state(tmp_path)["execution_position_care"]["state"] == "closed"
    definition = next(d for d in op.SERVICE_DEFINITIONS if d.service_id == "execution_position_care")
    monkeypatch.setattr(op, "_service_definition", lambda *_: replace(
        definition, command_sequence=(("scripts/run_paperops_autonomous_pass.py", "--scheduled"),)))
    with pytest.raises(ValueError, match="contract_invalid"):
        op.repair_operator_service_circuit("execution_position_care", explicit_position_care_confirmation=True)


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
