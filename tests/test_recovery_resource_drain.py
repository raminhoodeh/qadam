from datetime import datetime, timedelta, timezone
import os

import pytest

import orchestrator.qadam_operator_service as op
from orchestrator.runtime.scheduling import recovery_window_conflicts
from tests.test_qadam_operator_service_v2 import _ready_runtime, _settings, _success_executor, _write_json


@pytest.mark.parametrize("wait,blocked", [(299, False), (300, True), (1800, True)])
def test_waiting_repair_drains_conflicting_routine_starts_but_not_running_work(tmp_path, monkeypatch, wait, blocked):
    _ready_runtime(tmp_path)
    settings = _settings(tmp_path)
    definitions = {d.service_id: d for d in op.SERVICE_DEFINITIONS}
    now = datetime.now(timezone.utc)
    _write_json(tmp_path / op.FULL_HEAL_REQUEST_ARTIFACT,
                {"generated_at": (now-timedelta(seconds=wait)).isoformat()})
    _write_json(tmp_path / "qadam_operator_workers.json", {"workers": {
        "execution_context": {"service_id": "execution_context", "state": "running", "pid": os.getpid()}}})
    monkeypatch.setattr(op, "_last_successful_receipts", lambda _: {
        key: {"completed_at": now.isoformat()} for key in definitions})
    monkeypatch.setattr(op, "_fair_dispatch_order", lambda *a, **k: (
        [definitions["qeg_evidence_cycle"], definitions["source_ingestion"]], 0))
    monkeypatch.setattr(op, "_prerequisites_fresh", lambda *a, **k: (True, []))
    calls = []

    def execute(command, timeout):
        calls.append(command)
        return _success_executor(command, timeout)

    cycle = op.dispatch_due_jobs(settings, force_due=True, executor=execute, max_jobs=2,
                                 max_elapsed_seconds=120, recovery_service_ids=("qeg_evidence_cycle",))
    rows = {r["service_id"]: r for r in cycle["receipts"]}
    assert rows["qeg_evidence_cycle"]["skip_reason"] == "resource_claim_busy"
    if blocked:
        assert calls == []
        assert rows["source_ingestion"]["skip_reason"] == "recovery_resource_window_reserved"
        assert rows["source_ingestion"]["detail"]["waiting_recovery_services"] == ["qeg_evidence_cycle"]
        # Let the blocker finish naturally; the same owner can now run its repair.
        _write_json(tmp_path / "qadam_operator_workers.json", {"workers": {}})
        result = op.dispatch_due_jobs(settings, force_due=True, executor=execute,
            service_ids=("qeg_evidence_cycle",), recovery_service_ids=("qeg_evidence_cycle",))
        assert result["executed_count"] == 1
        assert result["failed_count"] == 0
    else:
        assert calls
    assert cycle["failed_count"] == 0


def test_reservation_preserves_critical_work_and_independent_resources():
    definitions = {d.service_id: d for d in op.SERVICE_DEFINITIONS}
    waiting = [definitions["qeg_evidence_cycle"]]
    for service_id in ("execution_position_care", "guarded_paperops", "execution_context",
                       "market_price_refresh", "paper_lifecycle_poll", "public_status_publication"):
        assert recovery_window_conflicts(definitions[service_id], waiting) == []
    assert recovery_window_conflicts(definitions["source_ingestion"], waiting) == ["qeg_evidence_cycle"]
    assert recovery_window_conflicts(definitions["source_ingestion"], []) == []


@pytest.mark.parametrize("hold", ["safety_circuit", "stale_prerequisite", "missing_dependency"])
def test_ineligible_repair_cannot_reserve_resources(tmp_path, monkeypatch, hold):
    _ready_runtime(tmp_path)
    settings = _settings(tmp_path)
    definitions = {d.service_id: d for d in op.SERVICE_DEFINITIONS}
    now = datetime.now(timezone.utc)
    _write_json(tmp_path / op.FULL_HEAL_REQUEST_ARTIFACT,
                {"generated_at": (now-timedelta(seconds=600)).isoformat()})
    _write_json(tmp_path / "qadam_operator_workers.json", {"workers": {
        "execution_context": {"service_id": "execution_context", "state": "running", "pid": os.getpid()}}})
    monkeypatch.setattr(op, "_last_successful_receipts", lambda _: {
        key: {"completed_at": now.isoformat()} for key in definitions
        if not (hold == "missing_dependency" and key == "strategy_research")})
    monkeypatch.setattr(op, "_fair_dispatch_order", lambda *a, **k: (
        [definitions["qeg_evidence_cycle"], definitions["source_ingestion"]], 0))
    monkeypatch.setattr(op, "_prerequisites_fresh", lambda _, d, **k:
        (False, ["stale"]) if hold == "stale_prerequisite" and d.service_id == "qeg_evidence_cycle" else (True, []))
    if hold == "safety_circuit":
        monkeypatch.setattr(op, "_circuit_breaker_state", lambda _: {
            "qeg_evidence_cycle": {"state": "open", "failure_class": "safety_violation"}})
        monkeypatch.setattr(op, "_circuit_revalidation_allowed", lambda *a: (False, ""))
    cycle = op.dispatch_due_jobs(settings, force_due=True, executor=_success_executor,
        max_jobs=2, max_elapsed_seconds=120, recovery_service_ids=("qeg_evidence_cycle",))
    source = next(r for r in cycle["receipts"] if r["service_id"] == "source_ingestion")
    assert source["state"] == "completed"
    assert cycle["failed_count"] == 0
