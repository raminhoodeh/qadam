from datetime import datetime, timedelta, timezone
from dataclasses import replace
import os

import pytest

import orchestrator.qadam_operator_service as op
from orchestrator.runtime.scheduling import order_by_deadline_slack, recovery_window_conflicts
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
    monkeypatch.setattr(op, "_wait_for_recovery_resource_window", lambda r, d, **k:
        ({"execution_context"}, ["execution_context"], 5.0))
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


@pytest.mark.parametrize("readonly", [True, False])
def test_only_readonly_downstream_conversion_yields_to_aged_input_repair(readonly):
    definitions = {d.service_id: d for d in op.SERVICE_DEFINITIONS}
    conversion = definitions["open_market_conversion"]
    if not readonly:
        conversion = replace(conversion, command_sequence=((
            "scripts/run_qadam_open_market_conversion.py", "--allow-network"),))
    repair = definitions["qualitative_evidence_cycle"]
    now = datetime.now(timezone.utc)
    critical = [definitions[s] for s in ("execution_position_care", "guarded_paperops",
                "execution_context", "market_price_refresh", "paper_lifecycle_poll")]
    order = [d.service_id for d in order_by_deadline_slack(
        [conversion, repair, *critical], {}, timestamp=now,
        recovery_targets={repair.service_id}, recovery_started_at=(now-timedelta(seconds=300)).isoformat())]
    assert (order.index(repair.service_id) < order.index(conversion.service_id)) is readonly
    assert all(order.index(d.service_id) < order.index(repair.service_id) for d in critical)
    assert recovery_window_conflicts(conversion, [repair]) == ([repair.service_id] if readonly else [])


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
    monkeypatch.setattr(op, "_wait_for_recovery_resource_window", lambda r, d, **k:
        ({"execution_context"}, ["execution_context"], 5.0))
    if hold == "safety_circuit":
        monkeypatch.setattr(op, "_circuit_breaker_state", lambda _: {
            "qeg_evidence_cycle": {"state": "open", "failure_class": "safety_violation"}})
        monkeypatch.setattr(op, "_circuit_revalidation_allowed", lambda *a: (False, ""))
    cycle = op.dispatch_due_jobs(settings, force_due=True, executor=_success_executor,
        max_jobs=2, max_elapsed_seconds=120, recovery_service_ids=("qeg_evidence_cycle",))
    source = next(r for r in cycle["receipts"] if r["service_id"] == "source_ingestion")
    assert source["state"] == "completed"
    assert cycle["failed_count"] == 0


def test_repair_rechecks_a_short_lived_worker_instead_of_reusing_batch_start_state(tmp_path, monkeypatch):
    definition = next(d for d in op.SERVICE_DEFINITIONS if d.service_id == "qualitative_evidence_cycle")
    snapshots = iter([{"execution_context"}, set()])
    monkeypatch.setattr(op, "_active_worker_service_ids", lambda _: next(snapshots))
    active, conflicts, waited = op._wait_for_recovery_resource_window(
        tmp_path, definition, maximum_wait_seconds=5, sleep=lambda _: None)
    assert active == set() and conflicts == []
    assert 0 <= waited <= 5


def test_repair_wait_is_bounded_and_never_claims_a_busy_resource_is_free(tmp_path, monkeypatch):
    definition = next(d for d in op.SERVICE_DEFINITIONS if d.service_id == "qualitative_evidence_cycle")
    monkeypatch.setattr(op, "_active_worker_service_ids", lambda _: {"execution_context"})
    ticks = iter(i / 4 for i in range(100))
    active, conflicts, waited = op._wait_for_recovery_resource_window(
        tmp_path, definition, maximum_wait_seconds=1000, clock=lambda: next(ticks), sleep=lambda _: None)
    assert active == {"execution_context"}
    assert conflicts == ["execution_context"]
    assert waited == 5
