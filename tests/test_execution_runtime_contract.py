"""Incident regressions: stale scheduler projections cannot revoke a fenced pass."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import os

import pytest

from orchestrator.config import Settings
from orchestrator.execution.contract import approve_execution_policy, bind_execution_contract, execution_contract_status
from orchestrator.execution.ledger import ExecutionOwnerError, OperatingLedger


@pytest.fixture
def ready(tmp_path, monkeypatch):
    settings = replace(Settings.from_env(), mode="paper", live_capital_enabled=False,
                       runtime_dir=str(tmp_path), state_root=str(tmp_path))
    files = {
        "qadam_experimental_paper_release_readiness.json": {
            "status": "experimental_paper_release_effective", "experimental_paper_release_effective": True,
            "experimental_paper_release_ready": True, "blockers": [], "paper_epoch_id": "epoch-test",
            "canonical_wrapper": "scripts/run_paperops_autonomous_pass.py"},
        "current_paper_epoch.json": {"paper_epoch_id": "epoch-test", "paper_epoch_kind": "clean_experimental_operator_epoch",
            "paper_growth_trial_calendar_started": True, "paper_growth_trial_state": "active_real_calendar",
            "simulated_elapsed_time": False, "paper_growth_trial_calendar_backfilled": False},
        "qadam_long_backtest_lock.json": {"status": "released", "paperops_watch_only_mode": False,
            "release_mode": "explicit_operator_approved_experimental_paper_epoch", "release_approval_epoch_id": "epoch-test"}}
    for name, body in files.items():
        (tmp_path / name).write_text(json.dumps(body))
    policy = approve_execution_policy(settings, reviewed=True)
    ledger = OperatingLedger(settings)
    lease = ledger.acquire_execution_owner(f"paperops-autonomous-pass:{os.getpid()}:test")
    for name, value in lease.environment().items():
        monkeypatch.setenv(name, value)
    bind_execution_contract(ledger, scope="entries_and_care")
    return settings, ledger, lease, policy


def test_exact_three_blocker_incident_does_not_revoke_database_ownership(ready):
    settings, ledger, lease, _ = ready
    runtime = ledger.store.path.parent
    (runtime / "qadam_operator_service_status.json").write_text(json.dumps({
        "service_running": False, "single_instance": {"owner_pid": 99999999},
        "services": [{"service_id": "guarded_paperops", "current_execution_allowed": False}]}))
    (runtime / "qadam_operator_service_lease.json").write_text("{}")
    from orchestrator.qadam_paperops_runtime_owner import paperops_runtime_owner_status
    status = paperops_runtime_owner_status(settings)
    assert status["active"]
    assert status["source"] == "canonical_database_contract"
    assert status["blockers"] == []
    assert ledger.assert_execution_owner()["owner_id"] == lease.owner_id


def test_scheduler_and_release_json_changes_are_not_live_execution_authority(ready):
    settings, ledger, _, _ = ready
    for name in ("current_paper_epoch.json", "qadam_experimental_paper_release_readiness.json", "qadam_long_backtest_lock.json"):
        (ledger.store.path.parent / name).write_text("{}")
    assert execution_contract_status(settings, require_entry=True)["active"]


def test_expired_lease_blocks_without_replaying_or_reacquiring(ready):
    settings, ledger, _, _ = ready
    old = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    with ledger.store.transaction() as db:
        db.execute("UPDATE execution_owner_leases SET expires_at=?", (old,))
    status = execution_contract_status(settings)
    assert not status["active"]
    assert "execution_owner_unavailable" in status["blockers"]


def test_wrong_token_cannot_claim_another_execution_owner(ready, monkeypatch):
    settings, _, _, _ = ready
    monkeypatch.setenv("QADAM_EXECUTION_OWNER_TOKEN", "wrong")
    assert "execution_owner_unavailable" in execution_contract_status(settings)["blockers"]
    assert "execution_owner_fencing_invalid" in execution_contract_status(settings)["blockers"]


def test_released_owner_and_old_contract_cannot_be_reused(ready):
    settings, ledger, lease, _ = ready
    ledger.release_execution_owner(lease)
    assert not execution_contract_status(settings)["active"]


def test_wrong_runtime_and_missing_database_fail_closed(ready, tmp_path):
    settings, _, _, _ = ready
    other = tmp_path / "missing"
    status = execution_contract_status(replace(settings, runtime_dir=str(other)))
    assert not status["active"]
    assert not other.exists()


def test_code_change_requires_reviewed_policy_installation(ready, monkeypatch):
    settings, _, _, _ = ready
    monkeypatch.setattr("orchestrator.execution.contract.code_digest", lambda: "different-build")
    assert "execution_policy_identity_mismatch" in execution_contract_status(settings)["blockers"]


def test_policy_tampering_does_not_create_authority(ready):
    settings, ledger, _, _ = ready
    with ledger.store.transaction() as db:
        db.execute("UPDATE execution_runtime_policy SET payload_json='{}'")
    assert not execution_contract_status(settings)["active"]


def test_care_scope_can_never_be_used_for_new_entry(ready):
    settings, ledger, _, _ = ready
    bind_execution_contract(ledger, scope="care_only")
    assert execution_contract_status(settings)["care_allowed"]
    assert not execution_contract_status(settings, require_entry=True)["active"]
    assert "execution_entry_scope_denied" in execution_contract_status(settings, require_entry=True)["blockers"]


def test_live_capital_and_unreviewed_policy_are_rejected(ready):
    settings, _, _, _ = ready
    assert not execution_contract_status(replace(settings, live_capital_enabled=True))["active"]
    with pytest.raises(ExecutionOwnerError):
        approve_execution_policy(settings)


def test_owner_observation_is_reused_without_scheduler_fallback(ready, monkeypatch):
    settings, _, _, _ = ready
    from orchestrator.paperops_active_paper_trading_automation import _automation_status
    owner = execution_contract_status(settings, require_entry=True)
    monkeypatch.setattr("orchestrator.qadam_paperops_runtime_owner.paperops_runtime_owner_status",
                        lambda *args: pytest.fail("Owner must not be re-read"))
    assert _automation_status({}, settings, owner_status=owner)["automation_active"]


def test_legacy_scheduler_check_is_retired_from_execution_sequence():
    from orchestrator.paperops_autonomous_pass import COMMAND_SEQUENCE
    commands = dict(COMMAND_SEQUENCE)
    assert commands["active_automation_check"] == ("scripts/check_qadam_execution_contract.py",)
    assert all("check_paperops_active_paper_trading_automation.py" not in command for _, command in COMMAND_SEQUENCE)


def test_position_care_is_independent_of_entry_dependencies_and_circuit():
    from orchestrator.runtime.services import SERVICE_DEFINITIONS
    from orchestrator.runtime.operator import service_recovery_contract_errors
    from orchestrator.runtime.scheduling import order_by_deadline_slack
    care = next(row for row in SERVICE_DEFINITIONS if row.service_id == "execution_position_care")
    entry = next(row for row in SERVICE_DEFINITIONS if row.service_id == "guarded_paperops")
    assert care.dependencies == () and not care.paperops_dependency
    assert care.command_sequence == (("scripts/run_paperops_autonomous_pass.py", "--care-only"),)
    assert care.cadence_seconds == 30
    assert service_recovery_contract_errors(care) == []
    ordered = order_by_deadline_slack((entry, care), {}, timestamp=datetime.now(timezone.utc))
    assert ordered[0] == care


def test_care_job_completes_without_invoking_entry_pipeline(ready, monkeypatch):
    import subprocess
    import sys
    from scripts import run_paperops_autonomous_pass as runner
    settings, ledger, lease, _ = ready
    ledger.release_execution_owner(lease)
    monkeypatch.setattr(Settings, "from_env", lambda: settings)
    monkeypatch.setattr(sys, "argv", ["run_paperops_autonomous_pass.py", "--care-only"])
    monkeypatch.setattr(runner, "_refresh_and_reconcile_paper_mirror",
                        lambda *a, **k: (subprocess.CompletedProcess([], 0, "", ""), {"status": "passed", "blockers": []}))
    monkeypatch.setattr("orchestrator.execution.care.protect_positions", lambda s: ({"status": "healthy_idle", "blockers": []}, []))
    monkeypatch.setattr("orchestrator.runtime.availability.record_care_sample", lambda *a, **k: None)
    monkeypatch.setattr(runner, "build_and_write_router_v3", lambda *a, **k: pytest.fail("Care cannot invoke entry routing"))
    assert runner.main() == 0
    result = json.loads((ledger.store.path.parent / "qadam_position_care_status.json").read_text())
    assert result["new_entry_submission_count"] == 0
    assert result["entry_review_invoked"] is False
    assert result["status"] == "position_care_completed"
    assert not (ledger.store.path.parent / "paperops_autonomous_pass_summary.json").exists()


def test_care_dispatches_with_entry_circuit_and_research_lock_open(tmp_path):
    from tests.test_qadam_operator_service_v2 import _ready_runtime, _settings, _success_executor
    from orchestrator.runtime.operator import dispatch_due_jobs
    _ready_runtime(tmp_path)
    (tmp_path / "qadam_operator_circuit_breakers.json").write_text(json.dumps({"services": {
        "guarded_paperops": {"state": "open", "failure_class": "safety_violation"}}}))
    cycle = dispatch_due_jobs(_settings(tmp_path),
                              service_ids=("guarded_paperops", "execution_position_care"),
                              executor=_success_executor)
    rows = {row["service_id"]: row for row in cycle["receipts"]}
    assert rows["execution_position_care"]["state"] == "completed"
    assert rows["guarded_paperops"]["state"] == "skipped"


def test_old_binding_cannot_survive_policy_generation_change(ready):
    settings, ledger, _, _ = ready
    with ledger.store.transaction() as db:
        db.execute("UPDATE execution_runtime_policy SET generation=generation+1")
    assert "execution_contract_binding_invalid" in execution_contract_status(settings)["blockers"]
